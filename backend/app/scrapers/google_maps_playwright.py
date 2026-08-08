"""Playwright Google Maps scraper — adapted from
https://github.com/kevmaindev/Googles-Maps-Scraper (master/main.py)

Uses direct Maps search URL (reliable in headless/Docker) + upstream
scroll / click / panel field extraction.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

AbortFn = Callable[[], bool]

_MAPS_BROWSER_LOCK: threading.Semaphore | None = None
_MAPS_LOCK_GUARD = threading.Lock()

# Upstream selectors (kevmaindev/Googles-Maps-Scraper)
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
                btn.first.click(timeout=2000)
                page.wait_for_timeout(600)
                return
        except Exception:
            continue


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


def _read_panel_upstream(
    page,
    *,
    keyword: str,
    location: str,
    fallback_name: str = "",
    require_no_website: bool = False,
) -> dict | None:
    """Extract fields the same way as kevmaindev/Googles-Maps-Scraper."""
    name = ""
    try:
        name = (page.locator("h1.DUwDvf").inner_text(timeout=2500) or "").strip()
    except Exception:
        try:
            name = (page.locator("h1.fontHeadlineLarge").inner_text(timeout=1200) or "").strip()
        except Exception:
            name = (fallback_name or "").strip()
    if not name or name.lower() in _SKIP_NAMES:
        return None

    address = ""
    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
    try:
        loc = page.locator(address_xpath)
        if loc.count() > 0:
            address = (loc.first.inner_text(timeout=1500) or "").strip()
    except Exception:
        address = ""

    website = ""
    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
    try:
        loc = page.locator(website_xpath)
        if loc.count() > 0:
            domain = (loc.first.inner_text(timeout=1500) or "").strip()
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

    if require_no_website and website:
        return None

    phone = ""
    phone_xpath = (
        '//button[contains(@data-item-id, "phone:tel:")]'
        '//div[contains(@class, "fontBodyMedium")]'
    )
    try:
        loc = page.locator(phone_xpath)
        if loc.count() > 0:
            phone = (loc.first.inner_text(timeout=1500) or "").strip()
    except Exception:
        phone = ""

    phone_unformatted = ""
    try:
        phone_btn = page.locator('button[data-item-id*="phone:tel:"]')
        if phone_btn.count() > 0:
            data_id = phone_btn.first.get_attribute("data-item-id") or ""
            if "phone:tel:" in data_id:
                phone_unformatted = data_id.split("phone:tel:", 1)[-1].strip()
            if not phone:
                aria = phone_btn.first.get_attribute("aria-label") or ""
                if aria.lower().startswith("phone:"):
                    phone = aria.split(":", 1)[-1].strip()
                else:
                    try:
                        phone = (phone_btn.first.inner_text(timeout=1000) or "").strip()
                    except Exception:
                        pass
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

    phone = re.sub(r"[^\d+\-\s().]", "", phone or "").strip()
    phone = re.sub(r"\s+", " ", phone).strip()
    digits = re.sub(r"\D", "", phone_unformatted or phone)
    if len(digits) < 8:
        return None
    if not phone_unformatted:
        phone_unformatted = digits

    reviews_count = None
    review_count_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//span'
    try:
        loc = page.locator(review_count_xpath)
        if loc.count() > 0:
            raw = (loc.first.inner_text(timeout=800) or "").strip()
            reviews_count = int(re.sub(r"[^\d]", "", raw.split()[0] or "") or 0) or None
    except Exception:
        reviews_count = None

    rating = None
    reviews_average_xpath = (
        '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]'
    )
    try:
        loc = page.locator(reviews_average_xpath)
        if loc.count() > 0:
            label = loc.first.get_attribute("aria-label") or ""
            rating = float(label.split()[0].replace(",", ".").strip())
    except Exception:
        try:
            label = page.locator('div[role="img"][aria-label*="star"]').first.get_attribute(
                "aria-label"
            ) or ""
            m = re.search(r"([\d.,]+)", label.replace(",", "."))
            if m:
                rating = float(m.group(1))
        except Exception:
            rating = None

    category = keyword
    try:
        cat = page.locator('button[jsaction*="category"]').first.inner_text(timeout=800)
        if cat:
            category = cat.strip()
    except Exception:
        pass

    lat, lng = _extract_coordinates_from_url(page.url)
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

    return {
        "title": name,
        "name": name,
        "phone": phone,
        "phoneUnformatted": phone_unformatted or phone,
        "email": None,
        "website": None if require_no_website else (website or None),
        "websiteUrl": None if require_no_website else (website or None),
        "address": address or None,
        "street": address or None,
        "city": city or None,
        "country": country or None,
        "categoryName": category or keyword or None,
        "categories": [category] if category else [],
        "totalScore": rating,
        "reviewsCount": reviews_count,
        "location": {"lat": lat, "lng": lng} if lat is not None else None,
        "url": page.url,
        "_playwright_maps": True,
    }


def scrape_google_maps_playwright(
    keyword: str,
    location: str,
    limit: int = 20,
    *,
    job_control: AbortFn | None = None,
    headless: bool = True,
    max_seconds: float = 120.0,
    require_no_website: bool = False,
) -> list[dict]:
    """
    Scrape Google Maps with Playwright (upstream field extraction).
    Returns Apify-like raw dicts (phone required).
    """
    keyword = (keyword or "").strip()
    location = (location or "").strip()
    limit = max(1, min(int(limit or 20), 40))
    if not keyword and not location:
        return []

    search_query = (
        f"{keyword} in {location}".strip() if keyword and location else (keyword or location)
    )
    per_card = 3.5 if require_no_website else 2.8
    budget = max(50.0, min(float(max_seconds or 90.0), 20.0 + limit * per_card))
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

    slot_wait_deadline = time.monotonic() + max(60.0, budget)
    acquired = False
    lock = _get_maps_lock()
    while time.monotonic() < slot_wait_deadline:
        if job_control and job_control():
            return []
        if lock.acquire(timeout=2.0):
            acquired = True
            break
    if not acquired:
        logger.warning("Playwright Maps: browser slot wait timed out — skipping %r", search_query)
        return []

    deadline = time.monotonic() + budget
    started = time.monotonic()

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
                page = context.new_page()
                page.set_default_timeout(10000)

                maps_url = "https://www.google.com/maps/search/" + quote_plus(search_query)
                logger.info(
                    "Playwright Maps: searching %r (limit=%s, budget=%.0fs)",
                    search_query,
                    limit,
                    budget,
                )
                # Direct search URL is reliable in headless (upstream search-box often times out)
                page.goto(maps_url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(1500)
                _dismiss_consent(page)
                page.wait_for_timeout(800)

                try:
                    page.wait_for_selector(_LISTING_CSS, timeout=15000)
                except Exception:
                    logger.warning("Playwright Maps: no listings for %r", search_query)
                    return results

                # Upstream scroll: hover + mouse.wheel
                try:
                    page.locator(_LISTING_CSS).first.hover(timeout=2500)
                except Exception:
                    pass

                previously_counted = 0
                stall_rounds = 0
                target = min(limit + 8, max(limit * 2, 12))
                if require_no_website:
                    target = min(max(limit * 3, 18), 50)
                while not aborted():
                    count = _listing_count(page)
                    if count >= target:
                        break
                    page.mouse.wheel(0, 10000)
                    page.wait_for_timeout(1800)
                    new_count = _listing_count(page)
                    if new_count <= previously_counted:
                        stall_rounds += 1
                        if stall_rounds >= 3:
                            break
                    else:
                        stall_rounds = 0
                        previously_counted = new_count

                try:
                    raw_links = page.locator(_LISTING_CSS).all()
                except Exception:
                    raw_links = page.locator(_LISTING_XPATH).all()

                max_scan = limit * 3 if require_no_website else max(limit * 2, limit + 6)
                listings: list[tuple] = []
                seen_aria: set[str] = set()
                for link in raw_links:
                    if len(listings) >= max_scan:
                        break
                    try:
                        aria = (link.get_attribute("aria-label") or "").strip()
                    except Exception:
                        aria = ""
                    key = aria.lower() if aria else ""
                    if key and (key in seen_aria or key in _SKIP_NAMES):
                        continue
                    if key:
                        seen_aria.add(key)
                    listings.append((link, aria))

                logger.info(
                    "Playwright Maps: opening %s cards (no_website=%s)",
                    len(listings),
                    require_no_website,
                )

                for link, aria_name in listings:
                    if aborted() or len(results) >= limit:
                        break
                    try:
                        # Click the place link itself (more reliable than parent in headless)
                        link.click(timeout=4000)
                        page.wait_for_timeout(1800)
                        try:
                            page.wait_for_selector(
                                'button[data-item-id*="phone:tel:"], a[data-item-id="authority"], button[data-item-id="address"], h1.DUwDvf',
                                timeout=3000,
                            )
                        except Exception:
                            page.wait_for_timeout(700)

                        item = _read_panel_upstream(
                            page,
                            keyword=keyword,
                            location=location,
                            fallback_name=aria_name,
                            require_no_website=require_no_website,
                        )
                        if not item:
                            continue
                        name_key = (item.get("title") or "").lower()
                        phone_key = re.sub(r"\D", "", item.get("phone") or "")
                        if name_key in seen_names or (phone_key and phone_key in seen_phones):
                            continue
                        seen_names.add(name_key)
                        if phone_key:
                            seen_phones.add(phone_key)
                        results.append(item)
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
