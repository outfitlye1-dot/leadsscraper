"""Playwright Google Maps scraper — adapted from
https://github.com/kevmaindev/Googles-Maps-Scraper

Fast path: scroll results feed → click each card → read side panel (no per-place navigation).
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

_LISTING_SEL = 'a[href*="/maps/place/"]'
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

_MAPS_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--disable-extensions",
    "--disable-background-networking",
    "--mute-audio",
    "--renderer-process-limit=2",
]


def _maps_concurrency() -> int:
    try:
        from app.core.config import get_settings

        return max(1, int(get_settings().SCRAPER_PLAYWRIGHT_MAPS_CONCURRENCY or 1))
    except Exception:
        return 1


def _maps_retries() -> int:
    try:
        from app.core.config import get_settings

        return max(1, min(int(get_settings().SCRAPER_PLAYWRIGHT_MAPS_RETRIES or 2), 4))
    except Exception:
        return 2


def _get_maps_lock() -> threading.Semaphore:
    global _MAPS_BROWSER_LOCK
    with _MAPS_LOCK_GUARD:
        if _MAPS_BROWSER_LOCK is None:
            _MAPS_BROWSER_LOCK = threading.Semaphore(_maps_concurrency())
        return _MAPS_BROWSER_LOCK


def _is_browser_crash(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "target crashed",
            "target closed",
            "browser has been closed",
            "browser closed",
            "page crashed",
            "has been closed",
        )
    )


def _safe_count(locator) -> int:
    try:
        return int(locator.count())
    except Exception:
        return -1


def _extract_coordinates_from_url(url: str) -> tuple[float | None, float | None]:
    try:
        part = url.split("/@")[-1].split("/")[0]
        lat_s, lng_s = part.split(",")[0], part.split(",")[1]
        return float(lat_s), float(lng_s)
    except Exception:
        return None, None


def _safe_text(page, selector: str, timeout: float = 1500) -> str:
    try:
        loc = page.locator(selector)
        if _safe_count(loc) <= 0:
            return ""
        return (loc.first.inner_text(timeout=timeout) or "").strip()
    except Exception:
        return ""


def _safe_attr(page, selector: str, attr: str, timeout: float = 1500) -> str:
    try:
        loc = page.locator(selector)
        if _safe_count(loc) <= 0:
            return ""
        return (loc.first.get_attribute(attr, timeout=timeout) or "").strip()
    except Exception:
        return ""


def _dismiss_consent(page) -> None:
    for sel in (
        'button:has-text("Accept all")',
        'button:has-text("Accept All")',
        'button:has-text("I agree")',
        'button[aria-label="Accept all"]',
        'button:has-text("Reject all")',
    ):
        try:
            btn = page.locator(sel)
            if _safe_count(btn) > 0:
                btn.first.click(timeout=1500)
                page.wait_for_timeout(400)
                return
        except Exception:
            continue


def _read_panel(
    page,
    *,
    fallback_name: str,
    keyword: str,
    location: str,
    require_no_website: bool = False,
) -> dict | None:
    name = (
        _safe_text(page, "h1.DUwDvf", 1200)
        or _safe_text(page, "h1.fontHeadlineLarge", 800)
        or fallback_name
    ).strip()
    if not name or name.lower() in _SKIP_NAMES:
        return None

    address = (
        _safe_attr(page, 'button[data-item-id="address"]', "aria-label")
        or _safe_text(page, 'button[data-item-id="address"]')
    )
    if address.lower().startswith("address:"):
        address = address.split(":", 1)[-1].strip()

    website = ""
    website_aria = _safe_attr(page, 'a[data-item-id="authority"]', "aria-label")
    website_text = _safe_text(page, 'a[data-item-id="authority"]')
    website_href = _safe_attr(page, 'a[data-item-id="authority"]', "href")
    for raw in (website_aria, website_text):
        if not raw:
            continue
        cleaned = re.sub(r"(?i)^website:\s*", "", raw).strip()
        if cleaned and "." in cleaned and " " not in cleaned and len(cleaned) < 80:
            website = cleaned if cleaned.startswith("http") else f"https://{cleaned}"
            break
    if not website and website_href and "http" in website_href:
        href_host = ""
        try:
            href_host = website_href.split("/")[2].lower()
        except Exception:
            href_host = ""
        if "google." in href_host:
            m = re.search(r"[?&](?:q|url)=([^&]+)", website_href)
            if m:
                from urllib.parse import unquote

                candidate = unquote(m.group(1)).split("&")[0]
                if candidate.startswith("http") and "google." not in candidate.split("/")[2]:
                    website = candidate
        else:
            website = website_href.split("&")[0].split("?")[0]

    # Target: businesses without a real website
    if require_no_website and website:
        return None

    phone = ""
    phone_unformatted = ""
    # Same as kevmaindev/Googles-Maps-Scraper: visible Maps text first
    try:
        phone_btn = page.locator('button[data-item-id*="phone:tel:"]')
        phone_count = _safe_count(phone_btn)
    except Exception:
        phone_count = -1
        phone_btn = None
    if phone_btn is not None and phone_count > 0:
        btn = phone_btn.first
        data_id = btn.get_attribute("data-item-id") or ""
        if "phone:tel:" in data_id:
            phone_unformatted = data_id.split("phone:tel:", 1)[-1].strip()
        try:
            visible = btn.locator("div.fontBodyMedium")
            if _safe_count(visible) > 0:
                phone = (visible.first.inner_text(timeout=1200) or "").strip()
        except Exception:
            phone = ""
        if not phone:
            phone_aria = btn.get_attribute("aria-label") or ""
            if phone_aria.lower().startswith("phone:"):
                phone = phone_aria.split(":", 1)[-1].strip()
            else:
                try:
                    phone = (btn.inner_text(timeout=1000) or "").strip()
                except Exception:
                    phone = ""
        if not phone and phone_unformatted:
            phone = phone_unformatted
    if not phone:
        tel = _safe_attr(page, 'a[href^="tel:"]', "href")
        if tel.startswith("tel:"):
            phone = tel[4:].strip()
            phone_unformatted = phone_unformatted or phone
    # Keep Maps display formatting (spaces/dashes) — only strip junk chars
    phone = re.sub(r"[^\d+\-\s().]", "", phone or "").strip()
    phone = re.sub(r"\s+", " ", phone).strip()
    digits = re.sub(r"\D", "", phone_unformatted or phone)
    if len(digits) < 8:
        return None
    if not phone_unformatted:
        phone_unformatted = digits

    # Rare on Maps, but capture if shown
    email = ""
    mailto = _safe_attr(page, 'a[href^="mailto:"]', "href")
    if mailto.lower().startswith("mailto:"):
        email = mailto.split(":", 1)[-1].split("?")[0].strip()
    if not email:
        email_aria = _safe_attr(page, 'button[data-item-id*="email"]', "aria-label")
        if email_aria and "@" in email_aria:
            m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", email_aria)
            if m:
                email = m.group(0)

    rating_label = _safe_attr(page, 'div[role="img"][aria-label*="star"]', "aria-label")
    rating = None
    if rating_label:
        m = re.search(r"([\d.,]+)", rating_label.replace(",", "."))
        if m:
            try:
                rating = float(m.group(1))
            except ValueError:
                rating = None

    reviews_text = _safe_text(page, 'button[jsaction*="reviewChart"]') or _safe_text(
        page, 'div[jsaction*="reviewChart"] span'
    )
    reviews_count = None
    if reviews_text:
        m = re.search(r"([\d,]+)", reviews_text.replace(",", ""))
        if m:
            try:
                reviews_count = int(m.group(1))
            except ValueError:
                reviews_count = None

    category = _safe_text(page, 'button[jsaction*="category"]') or keyword
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
        "email": email or None,
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


def _run_maps_session(
    *,
    search_query: str,
    keyword: str,
    location: str,
    limit: int,
    headless: bool,
    require_no_website: bool,
    aborted: AbortFn,
    deadline: float,
) -> list[dict]:
    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    seen_names: set[str] = set()
    seen_phones: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=_MAPS_LAUNCH_ARGS)
        try:
            context = browser.new_context(
                locale="en-GB",
                viewport={"width": 1024, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.set_default_timeout(8000)

            maps_url = "https://www.google.com/maps/search/" + quote_plus(search_query)
            logger.info(
                "Playwright Maps: searching %r (limit=%s)",
                search_query,
                limit,
            )
            page.goto(maps_url, wait_until="domcontentloaded", timeout=12000)
            page.wait_for_timeout(500)
            _dismiss_consent(page)

            try:
                page.wait_for_selector(_LISTING_SEL, timeout=7000)
            except Exception:
                logger.warning("Playwright Maps: no listings for %r", search_query)
                return results

            # Scroll feed until we have enough cards (or stall / crash)
            feed = page.locator('div[role="feed"]')
            previously_counted = 0
            stall_rounds = 0
            while not aborted():
                count = _safe_count(page.locator(_LISTING_SEL))
                if count < 0:
                    raise RuntimeError("Locator.count: Target crashed")
                target_cards = min(limit + 6, max(limit * 2, 12))
                if require_no_website:
                    target_cards = min(max(limit * 3, 18), 40)
                if count >= target_cards:
                    break
                try:
                    if _safe_count(feed) > 0:
                        feed.first.evaluate("el => { el.scrollTop = el.scrollHeight; }")
                    else:
                        page.mouse.wheel(0, 4000)
                except Exception as scroll_exc:
                    if _is_browser_crash(scroll_exc):
                        raise
                    page.mouse.wheel(0, 4000)
                page.wait_for_timeout(500)
                new_count = _safe_count(page.locator(_LISTING_SEL))
                if new_count < 0:
                    raise RuntimeError("Locator.count: Target crashed")
                if new_count <= previously_counted:
                    stall_rounds += 1
                    if stall_rounds >= 2:
                        break
                else:
                    stall_rounds = 0
                    previously_counted = new_count

            try:
                raw_links = page.locator(_LISTING_SEL).all()
            except Exception as exc:
                if _is_browser_crash(exc):
                    raise
                logger.warning("Playwright Maps: listing snapshot failed: %s", exc)
                return results

            listings = []
            seen_aria: set[str] = set()
            for link in raw_links:
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
                max_scan = limit * 3 if require_no_website else limit * 2
                if len(listings) >= max_scan:
                    break

            logger.info(
                "Playwright Maps: opening %s cards (no_website=%s)",
                len(listings),
                require_no_website,
            )

            for link, aria_name in listings:
                if aborted() or len(results) >= limit:
                    break
                try:
                    link.click(timeout=3500)
                    try:
                        page.wait_for_selector(
                            'button[data-item-id*="phone:tel:"], a[data-item-id="authority"], button[data-item-id="address"]',
                            timeout=2800,
                        )
                    except Exception:
                        page.wait_for_timeout(700)

                    item = _read_panel(
                        page,
                        fallback_name=aria_name,
                        keyword=keyword,
                        location=location,
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
                    if _is_browser_crash(exc):
                        if results:
                            logger.warning(
                                "Playwright Maps: browser crashed after %s leads — returning partial",
                                len(results),
                            )
                            return results
                        raise
                    logger.debug("Playwright Maps listing failed: %s", exc)
                    continue
        finally:
            try:
                browser.close()
            except Exception:
                pass

    return results


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
    Scrape Google Maps business listings with Playwright.

    Returns Apify-like raw dicts (phone required).
    When require_no_website=True, skips businesses that list a website on Maps.
    """
    keyword = (keyword or "").strip()
    location = (location or "").strip()
    limit = max(1, min(int(limit or 20), 40))
    if not keyword and not location:
        return []

    search_query = (
        f"{keyword} in {location}".strip() if keyword and location else (keyword or location)
    )
    # No-website mode needs more cards scanned (many listings have sites)
    per_card = 3.2 if require_no_website else 2.4
    budget = max(35.0, min(float(max_seconds or 75.0), 15.0 + limit * per_card))
    deadline = time.monotonic() + budget

    def aborted() -> bool:
        if time.monotonic() >= deadline:
            return True
        return bool(job_control and job_control())

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        logger.error("playwright not installed — cannot scrape Google Maps locally")
        return []

    # Queue for a free browser slot — waiting does NOT burn the scrape budget.
    slot_wait_deadline = time.monotonic() + max(45.0, budget)
    acquired = False
    lock = _get_maps_lock()
    while time.monotonic() < slot_wait_deadline:
        if job_control and job_control():
            return []
        if lock.acquire(timeout=1.5):
            acquired = True
            break
    if not acquired:
        logger.warning("Playwright Maps: browser slot wait timed out — skipping %r", search_query)
        return []

    # Fresh scrape clock after we own a browser
    deadline = time.monotonic() + budget
    attempts = _maps_retries()
    results: list[dict] = []
    last_exc: BaseException | None = None

    try:
        for attempt in range(1, attempts + 1):
            if aborted():
                break
            try:
                results = _run_maps_session(
                    search_query=search_query,
                    keyword=keyword,
                    location=location,
                    limit=limit,
                    headless=headless,
                    require_no_website=require_no_website,
                    aborted=aborted,
                    deadline=deadline,
                )
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if _is_browser_crash(exc) and attempt < attempts and not aborted():
                    logger.warning(
                        "Playwright Maps: Chromium crashed (attempt %s/%s) for %r — retrying",
                        attempt,
                        attempts,
                        search_query,
                    )
                    time.sleep(1.2 * attempt)
                    continue
                if _is_browser_crash(exc):
                    logger.error(
                        "Playwright Maps: Chromium crashed for %r after %s attempts: %s",
                        search_query,
                        attempt,
                        exc,
                    )
                    break
                raise
    finally:
        lock.release()

    if last_exc and not results and _is_browser_crash(last_exc):
        raise RuntimeError(
            "Google Maps browser crashed (often low memory on the server). "
            "Try again with a smaller limit, or upgrade Railway memory."
        ) from last_exc
    if last_exc and not results:
        raise last_exc

    logger.info(
        "Playwright Maps: extracted %s phone leads for %r in %.1fs",
        len(results),
        search_query,
        budget - max(0.0, deadline - time.monotonic()),
    )
    return results[:limit]
