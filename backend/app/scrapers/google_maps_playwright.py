"""Playwright Google Maps scraper — adapted from
https://github.com/kevmaindev/Googles-Maps-Scraper (master/main.py)

Fast path: read phones from result cards, then click only cards still missing a phone.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable
from urllib.parse import quote_plus, unquote

logger = logging.getLogger(__name__)

AbortFn = Callable[[], bool]

_MAPS_BROWSER_LOCK: threading.Semaphore | None = None
_MAPS_LOCK_GUARD = threading.Lock()

_LISTING_XPATH = '//a[contains(@href, "/maps/place")]'
_LISTING_CSS = 'a[href*="/maps/place/"]'
_SKIP_NAMES = frozenset(
    {
        "results",
        "sponsored",
        "overview",
        "about",
        "updates",
        "photos",
        "reviews",
    }
)
_PHONE_RE = re.compile(
    r"(?:\+|00)[1-9][\d\s().-]{6,16}\d|(?<!\d)0\d(?:[\s().-]?\d){8,13}(?!\d)"
)


def _maps_concurrency() -> int:
    try:
        from app.core.config import get_settings

        return max(1, int(get_settings().SCRAPER_PLAYWRIGHT_MAPS_CONCURRENCY or 1))
    except Exception:
        return 1


def _get_maps_lock() -> threading.Semaphore:
    global _MAPS_BROWSER_LOCK
    with _MAPS_LOCK_GUARD:
        if _MAPS_BROWSER_LOCK is None:
            _MAPS_BROWSER_LOCK = threading.Semaphore(_maps_concurrency())
        return _MAPS_BROWSER_LOCK


def _extract_coordinates_from_url(url: str) -> tuple[float | None, float | None]:
    try:
        part = url.split("/@")[-1].split("/")[0]
        return float(part.split(",")[0]), float(part.split(",")[1])
    except Exception:
        return None, None


def _normalize_phone(raw: str) -> tuple[str, str]:
    phone = re.sub(r"[^\d+\-\s().]", "", raw or "").strip()
    phone = re.sub(r"\s+", " ", phone).strip()
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8:
        return "", ""
    return phone, digits


def _phone_from_text(text: str) -> str:
    if not text:
        return ""
    for match in _PHONE_RE.findall(text):
        phone, digits = _normalize_phone(match)
        if phone and len(digits) >= 8:
            return phone
    return ""


def _dismiss_consent(page) -> None:
    for sel in (
        'button:has-text("Accept all")',
        'button:has-text("Accept All")',
        'button:has-text("I agree")',
        'button[aria-label="Accept all"]',
        'button:has-text("Reject all")',
        'button:has-text("Reject All")',
    ):
        try:
            btn = page.locator(sel)
            if btn.count() > 0:
                btn.first.click(timeout=1500)
                page.wait_for_timeout(400)
                return
        except Exception:
            continue


def _page_blocked(page) -> bool:
    try:
        html = (page.content() or "").lower()
    except Exception:
        return False
    return any(
        token in html
        for token in (
            "unusual traffic",
            "detected unusual",
            "our systems have detected",
            "enable javascript",
            "captcha",
            "recaptcha",
        )
    )


def _listing_count(page) -> int:
    try:
        n = page.locator(_LISTING_CSS).count()
        if n > 0:
            return n
    except Exception:
        pass
    try:
        return page.locator(_LISTING_XPATH).count()
    except Exception:
        return 0


def _feed_cards(page) -> list[dict]:
    try:
        return page.evaluate(
            """() => {
              const cards = [];
              const seen = new Set();
              const links = document.querySelectorAll('a[href*="/maps/place/"]');
              for (const a of links) {
                const href = a.href || '';
                const name = (a.getAttribute('aria-label') || '').trim();
                const key = (name || href).toLowerCase();
                if (!key || seen.has(key)) continue;
                seen.add(key);
                const root = a.closest('div[role="article"]')
                  || a.closest('div[jsaction]')
                  || a.parentElement;
                const text = root && root.innerText ? root.innerText.slice(0, 500) : '';
                cards.push({ name, href, text });
              }
              return cards;
            }"""
        ) or []
    except Exception as exc:
        logger.debug("Playwright Maps: feed extract failed: %s", exc)
        return []


def _city_country(location: str) -> tuple[str, str]:
    city = ""
    country = ""
    if location and "," in location:
        parts = [p.strip() for p in location.split(",") if p.strip()]
        if parts:
            city = parts[0]
        if len(parts) > 1:
            country = parts[-1]
    elif location:
        city = location
    return city, country


def _lead_dict(
    *,
    name: str,
    phone: str,
    phone_unformatted: str,
    website: str | None,
    address: str | None,
    keyword: str,
    location: str,
    url: str,
    category: str | None = None,
    rating: float | None = None,
    reviews_count: int | None = None,
) -> dict:
    city, country = _city_country(location)
    lat, lng = _extract_coordinates_from_url(url)
    cat = category or keyword
    return {
        "title": name,
        "name": name,
        "phone": phone,
        "phoneUnformatted": phone_unformatted or phone,
        "email": None,
        "website": website or None,
        "websiteUrl": website or None,
        "address": address or None,
        "street": address or None,
        "city": city or None,
        "country": country or None,
        "categoryName": cat or None,
        "categories": [cat] if cat else [],
        "totalScore": rating,
        "reviewsCount": reviews_count,
        "location": {"lat": lat, "lng": lng} if lat is not None else None,
        "url": url,
        "_playwright_maps": True,
    }


def _read_panel_upstream(
    page,
    *,
    keyword: str,
    location: str,
    fallback_name: str = "",
) -> dict | None:
    """Extract fields the same way as kevmaindev/Googles-Maps-Scraper."""
    name = ""
    try:
        name = (page.locator("h1.DUwDvf").inner_text(timeout=1200) or "").strip()
    except Exception:
        try:
            name = (page.locator("h1.fontHeadlineLarge").inner_text(timeout=800) or "").strip()
        except Exception:
            name = (fallback_name or "").strip()
    if not name or name.lower() in _SKIP_NAMES:
        return None

    address = ""
    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
    try:
        loc = page.locator(address_xpath)
        if loc.count() > 0:
            address = (loc.first.inner_text(timeout=800) or "").strip()
    except Exception:
        address = ""

    website = ""
    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
    try:
        loc = page.locator(website_xpath)
        if loc.count() > 0:
            domain = (loc.first.inner_text(timeout=800) or "").strip()
            domain = re.sub(r"(?i)^website:\s*", "", domain).strip()
            if domain:
                website = domain if domain.startswith("http") else f"https://{domain}"
    except Exception:
        website = ""
    if not website:
        try:
            href = page.locator('a[data-item-id="authority"]').first.get_attribute("href") or ""
            host = href.split("/")[2].lower() if href.startswith("http") else ""
            if href.startswith("http") and "google." not in host:
                website = href.split("&")[0].split("?")[0]
        except Exception:
            pass

    phone = ""
    phone_unformatted = ""
    phone_xpath = (
        '//button[contains(@data-item-id, "phone:tel:")]'
        '//div[contains(@class, "fontBodyMedium")]'
    )
    try:
        loc = page.locator(phone_xpath)
        if loc.count() > 0:
            phone = (loc.first.inner_text(timeout=800) or "").strip()
    except Exception:
        phone = ""
    try:
        phone_btn = page.locator('button[data-item-id*="phone:tel:"]')
        if phone_btn.count() > 0:
            data_id = phone_btn.first.get_attribute("data-item-id") or ""
            if "phone:tel:" in data_id:
                phone_unformatted = unquote(data_id.split("phone:tel:", 1)[-1].strip())
            if not phone:
                aria = phone_btn.first.get_attribute("aria-label") or ""
                if aria.lower().startswith("phone:"):
                    phone = aria.split(":", 1)[-1].strip()
    except Exception:
        pass
    if not phone and phone_unformatted:
        phone = phone_unformatted
    if not phone:
        try:
            tel = page.locator('a[href^="tel:"]').first.get_attribute("href") or ""
            if tel.startswith("tel:"):
                phone = tel[4:].strip()
                phone_unformatted = phone_unformatted or phone
        except Exception:
            pass
    if not phone:
        try:
            phone = _phone_from_text(page.locator("div[role='main']").first.inner_text(timeout=600))
        except Exception:
            pass

    phone, digits = _normalize_phone(phone_unformatted or phone)
    if len(digits) < 8:
        return None

    category = keyword
    try:
        cat = page.locator('button[jsaction*="category"]').first.inner_text(timeout=500)
        if cat:
            category = cat.strip()
    except Exception:
        pass

    return _lead_dict(
        name=name,
        phone=phone,
        phone_unformatted=digits,
        website=website or None,
        address=address or None,
        keyword=keyword,
        location=location,
        url=page.url,
        category=category,
    )


def scrape_google_maps_playwright(
    keyword: str,
    location: str,
    limit: int = 20,
    *,
    job_control: AbortFn | None = None,
    headless: bool = True,
    max_seconds: float = 70.0,
    require_no_website: bool = False,
) -> list[dict]:
    """Scrape Google Maps listings with Playwright. Phone required."""
    keyword = (keyword or "").strip()
    location = (location or "").strip()
    limit = max(1, min(int(limit or 20), 40))
    if not keyword and not location:
        return []

    search_query = (
        f"{keyword} in {location}".strip() if keyword and location else (keyword or location)
    )
    budget = max(28.0, min(float(max_seconds or 55.0), 10.0 + limit * 2.2))
    deadline = time.monotonic() + budget

    def aborted() -> bool:
        if time.monotonic() >= deadline:
            return True
        return bool(job_control and job_control())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright not installed — cannot scrape Google Maps locally")
        return []

    results: list[dict] = []
    seen_names: set[str] = set()
    seen_phones: set[str] = set()

    slot_wait_deadline = time.monotonic() + 25.0
    acquired = False
    lock = _get_maps_lock()
    while time.monotonic() < slot_wait_deadline:
        if job_control and job_control():
            return []
        if lock.acquire(timeout=1.0):
            acquired = True
            break
    if not acquired:
        logger.warning("Playwright Maps: browser slot wait timed out — skipping %r", search_query)
        return []

    deadline = time.monotonic() + budget
    started = time.monotonic()

    def add_item(item: dict | None) -> None:
        if not item:
            return
        name_key = (item.get("title") or "").lower()
        phone_key = re.sub(r"\D", "", item.get("phone") or "")
        if not name_key or name_key in _SKIP_NAMES:
            return
        if name_key in seen_names or (phone_key and phone_key in seen_phones):
            return
        if require_no_website and item.get("website"):
            return
        seen_names.add(name_key)
        if phone_key:
            seen_phones.add(phone_key)
        results.append(item)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            try:
                context = browser.new_context(
                    locale="en-GB",
                    viewport={"width": 1280, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                )
                context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                )
                page = context.new_page()
                page.set_default_timeout(6000)

                maps_url = "https://www.google.com/maps/search/" + quote_plus(search_query)
                logger.info(
                    "Playwright Maps: searching %r (limit=%s, budget=%.0fs)",
                    search_query,
                    limit,
                    budget,
                )
                page.goto(maps_url, wait_until="domcontentloaded", timeout=18000)
                page.wait_for_timeout(700)
                _dismiss_consent(page)

                try:
                    page.wait_for_selector(_LISTING_CSS, timeout=8000)
                except Exception:
                    if _page_blocked(page):
                        raise RuntimeError(
                            "Google Maps blocked this server (captcha / unusual traffic). "
                            "Try again later or scrape from a machine with a residential IP."
                        )
                    logger.warning("Playwright Maps: no listings for %r", search_query)
                    return results

                # Light scroll — enough cards, not a long stall
                try:
                    page.locator(_LISTING_CSS).first.hover(timeout=1500)
                except Exception:
                    pass
                previously = 0
                stalls = 0
                target = min(max(limit + 4, 8), 18)
                while not aborted() and _listing_count(page) < target and stalls < 2:
                    page.mouse.wheel(0, 8000)
                    page.wait_for_timeout(700)
                    n = _listing_count(page)
                    if n <= previously:
                        stalls += 1
                    else:
                        stalls = 0
                        previously = n

                cards = _feed_cards(page)
                logger.info("Playwright Maps: %s feed cards for %r", len(cards), search_query)

                # Fast path: phones already visible on result cards
                for card in cards:
                    if aborted() or len(results) >= limit:
                        break
                    name = (card.get("name") or "").strip()
                    if not name or name.lower() in _SKIP_NAMES:
                        continue
                    phone = _phone_from_text(card.get("text") or "")
                    if not phone:
                        continue
                    phone, digits = _normalize_phone(phone)
                    add_item(
                        _lead_dict(
                            name=name,
                            phone=phone,
                            phone_unformatted=digits,
                            website=None,
                            address=None,
                            keyword=keyword,
                            location=location,
                            url=card.get("href") or page.url,
                        )
                    )

                # Click only cards still missing a phone (same DOM order as feed extract)
                for index, card in enumerate(cards):
                    if aborted() or len(results) >= limit:
                        break
                    name = (card.get("name") or "").strip()
                    if not name or name.lower() in seen_names or name.lower() in _SKIP_NAMES:
                        continue
                    try:
                        loc = page.locator(_LISTING_CSS).nth(index)
                        loc.click(timeout=2500)
                        try:
                            page.wait_for_selector(
                                'button[data-item-id*="phone:tel:"], a[href^="tel:"], h1.DUwDvf',
                                timeout=1800,
                            )
                        except Exception:
                            page.wait_for_timeout(350)
                        item = _read_panel_upstream(
                            page,
                            keyword=keyword,
                            location=location,
                            fallback_name=name,
                        )
                        add_item(item)
                    except Exception as exc:
                        logger.debug("Playwright Maps listing failed: %s", exc)
                        continue
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    finally:
        lock.release()

    logger.info(
        "Playwright Maps: extracted %s phone leads for %r in %.1fs",
        len(results),
        search_query,
        time.monotonic() - started,
    )
    return results[:limit]
