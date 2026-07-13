import logging
import random
import threading
from contextlib import contextmanager

from app.core.config import get_settings
from app.scraper.utils.user_agents import get_random_user_agent
from app.scrapers.ai_selectors import DEFAULT_CONTACT_SELECTORS, get_cached_selectors, repair_selectors

logger = logging.getLogger(__name__)

STEALTH_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
]

CONTACT_SELECTORS = DEFAULT_CONTACT_SELECTORS


class PlaywrightPool:
    """Enterprise browser pool: context reuse, human-like behavior, stealth."""

    def __init__(self):
        self._lock = threading.Lock()
        self._playwright = None
        self._browser = None
        self._contexts: list = []
        self._max_contexts = max(1, get_settings().SCRAPER_PLAYWRIGHT_CONTEXTS)

    def _ensure_browser(self):
        from playwright.sync_api import sync_playwright

        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=STEALTH_LAUNCH_ARGS,
            )

    def _acquire_context(self):
        self._ensure_browser()
        if self._contexts:
            return self._contexts.pop()
        return self._browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={
                "width": random.randint(1280, 1600),
                "height": random.randint(720, 1000),
            },
            locale=random.choice(["en-US", "en-GB", "de-DE"]),
            java_script_enabled=True,
            timezone_id=random.choice(["Europe/London", "Europe/Berlin", "America/New_York"]),
        )

    def _release_context(self, context) -> None:
        if len(self._contexts) < self._max_contexts:
            try:
                for page in context.pages:
                    page.close()
            except Exception:
                pass
            self._contexts.append(context)
        else:
            try:
                context.close()
            except Exception:
                pass

    def _human_behavior(self, page, *, scroll: bool) -> None:
        fast = get_settings().SCRAPER_FAST_MODE
        try:
            page.mouse.move(random.randint(100, 400), random.randint(80, 300))
        except Exception:
            pass
        if scroll:
            for frac in (0.25, 0.5, 0.75):
                try:
                    page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {frac})")
                    page.wait_for_timeout(random.randint(150, 400) if fast else random.randint(300, 700))
                except Exception:
                    break
        page.wait_for_timeout(random.randint(120, 280) if fast else random.randint(250, 600))

    def fetch(self, url: str, timeout_ms: int = 15000, *, human_scroll: bool = False) -> str | None:
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            logger.warning("Playwright not installed — JS rendering unavailable")
            return None

        fast = get_settings().SCRAPER_FAST_MODE

        with self._lock:
            context = None
            try:
                context = self._acquire_context()
                page = context.new_page()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    try:
                        page.wait_for_load_state("networkidle", timeout=min(6000, timeout_ms // 2))
                    except Exception:
                        pass

                    cached = get_cached_selectors(url)
                    selectors = cached.all_selectors() if cached else list(CONTACT_SELECTORS)
                    for selector in selectors:
                        try:
                            page.wait_for_selector(selector, timeout=800 if fast else 1500)
                            break
                        except Exception:
                            continue

                    self._human_behavior(page, scroll=human_scroll)
                    html = page.content()[:500_000]
                    if cached and not repair_selectors(html, url, []):
                        pass
                    return html
                finally:
                    page.close()
            except Exception as exc:
                logger.debug("Playwright pool fetch failed for %s: %s", url, exc)
                self._shutdown_unlocked()
                return None
            finally:
                if context is not None:
                    self._release_context(context)

    def close(self) -> None:
        with self._lock:
            self._shutdown_unlocked()

    def _shutdown_unlocked(self) -> None:
        for ctx in self._contexts:
            try:
                ctx.close()
            except Exception:
                pass
        self._contexts.clear()
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._playwright = None


_pool: PlaywrightPool | None = None
_pool_lock = threading.Lock()


def get_playwright_pool() -> PlaywrightPool:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = PlaywrightPool()
        return _pool


@contextmanager
def playwright_session():
    pool = get_playwright_pool()
    try:
        yield pool
    finally:
        pool.close()
        global _pool
        with _pool_lock:
            _pool = None
