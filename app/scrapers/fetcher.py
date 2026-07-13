import logging
import threading
import time
from collections.abc import Callable

import requests

from app.core.config import get_settings
from app.scraper.logging.scrape_logger import log_fetch_failure, log_fetch_success
from app.scraper.metrics import ScrapeMetrics
from app.scraper.utils.anti_bot import detect_bot_block
from app.scraper.utils.delays import random_delay
from app.scraper.utils.domain_throttle import wait_for_domain
from app.scraper.utils.proxy import get_next_proxy, proxy_dict_for_requests
from app.scraper.utils.user_agents import get_random_user_agent
from app.scrapers.js_detect import is_useful_html, looks_like_js_shell
from app.scrapers.robots import is_allowed
from app.scrapers.strategy_router import FetchStrategy, decide_strategy

logger = logging.getLogger(__name__)


class PageFetcher:
    """Enterprise fetcher: strategy routing, proxy rotation, anti-bot, retries."""

    def __init__(
        self,
        timeout: float | None = None,
        use_playwright: bool | None = None,
        metrics: ScrapeMetrics | None = None,
        job_control: Callable[[], bool] | None = None,
    ):
        settings = get_settings()
        self.timeout = timeout if timeout is not None else settings.SCRAPER_TIMEOUT
        self.use_playwright = (
            use_playwright
            if use_playwright is not None
            else settings.SCRAPER_ENABLE_PLAYWRIGHT
        )
        self.retries = max(settings.SCRAPER_FETCH_RETRIES, 2)
        self.metrics = metrics
        self.job_control = job_control
        self._local = threading.local()
        self._start_time = time.monotonic()
        self._request_count = 0

    def _aborted(self) -> bool:
        return bool(self.job_control and self.job_control())

    def _get_session(self) -> requests.Session:
        if not getattr(self._local, "session", None):
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": get_random_user_agent(),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Cache-Control": "no-cache",
                }
            )
            self._local.session = session
        return self._local.session

    def _track_request(self) -> None:
        self._request_count += 1
        if self.metrics:
            elapsed = max(time.monotonic() - self._start_time, 0.1)
            self.metrics.requests_per_minute = round(self._request_count / elapsed * 60, 1)

    def fetch(self, url: str) -> tuple[str | None, str]:
        if self._aborted():
            return None, url

        settings = get_settings()
        if settings.SCRAPER_RESPECT_ROBOTS and not is_allowed(url):
            log_fetch_failure(self.metrics, url, "blocked by robots.txt")
            return None, url

        random_delay()
        wait_for_domain(url)
        url = self._normalize_url(url)
        session = self._get_session()
        session.headers["User-Agent"] = get_random_user_agent()

        html: str | None = None
        last_error = "empty response"
        status_code: int | None = None
        proxy = get_next_proxy()
        proxies = proxy_dict_for_requests(proxy)

        for attempt in range(1, self.retries + 1):
            if self._aborted():
                return None, url
            try:
                self._track_request()
                response = session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    proxies=proxies,
                )
                status_code = response.status_code
                if response.status_code >= 400:
                    last_error = f"HTTP {response.status_code}"
                    block = detect_bot_block(None, status_code=status_code, headers=dict(response.headers))
                    if block.blocked and self.metrics:
                        self.metrics.inc("bot_blocks")
                    if block.should_switch_proxy and proxy:
                        proxy = get_next_proxy()
                        proxies = proxy_dict_for_requests(proxy)
                        if self.metrics:
                            self.metrics.inc("proxy_switches")
                    if attempt < self.retries:
                        time.sleep(0.5 * (2 ** (attempt - 1)))
                        if self.metrics:
                            self.metrics.inc("retry_count")
                        continue
                    break
                response.encoding = response.encoding or "utf-8"
                html = response.text[:500_000]
                block = detect_bot_block(html, status_code=status_code, headers=dict(response.headers))
                if block.blocked:
                    last_error = block.message
                    if self.metrics:
                        self.metrics.inc("bot_blocks")
                    if block.should_switch_proxy:
                        proxy = get_next_proxy()
                        proxies = proxy_dict_for_requests(proxy)
                        if self.metrics:
                            self.metrics.inc("proxy_switches")
                    if block.should_use_browser:
                        break
                    if attempt < self.retries and block.should_retry:
                        time.sleep(0.5 * (2 ** (attempt - 1)))
                        if self.metrics:
                            self.metrics.inc("retry_count")
                        continue
                    break
                if html and is_useful_html(html):
                    decision = decide_strategy(url, html, status_code=status_code)
                    if decision.strategy == FetchStrategy.http:
                        if self.metrics:
                            self.metrics.inc("strategy_http")
                        log_fetch_success(self.metrics, url)
                        return html, url
                    if decision.strategy == FetchStrategy.playwright:
                        break
                    if decision.strategy == FetchStrategy.api_intercept:
                        if self.metrics:
                            self.metrics.inc("strategy_api")
                if html and looks_like_js_shell(html):
                    last_error = "JS-rendered page shell"
                    break
                last_error = "thin HTML"
            except Exception as exc:
                last_error = str(exc)
                logger.debug("Requests fetch attempt %s failed for %s: %s", attempt, url, exc)
                if attempt < self.retries:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    if self.metrics:
                        self.metrics.inc("retry_count")
                    proxy = get_next_proxy()
                    proxies = proxy_dict_for_requests(proxy)

        decision = decide_strategy(url, html, status_code=status_code, force_playwright=False)
        if self.use_playwright and (
            decision.strategy in (FetchStrategy.playwright, FetchStrategy.api_intercept)
            or looks_like_js_shell(html or "")
            or (html and not is_useful_html(html))
        ):
            dynamic_html = self._fetch_playwright(url, scroll=decision.needs_scroll)
            if dynamic_html and is_useful_html(dynamic_html):
                if self.metrics:
                    self.metrics.inc("js_render_used")
                    self.metrics.inc("strategy_playwright")
                    self.metrics.inc("browser_renders")
                log_fetch_success(self.metrics, url)
                return dynamic_html, url
            if dynamic_html:
                html = dynamic_html

        if html:
            if self.metrics:
                self.metrics.inc("strategy_http")
            log_fetch_success(self.metrics, url)
            return html, url

        log_fetch_failure(self.metrics, url, last_error)
        return None, url

    def _normalize_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return f"https://{url}"
        return url

    def _fetch_playwright(self, url: str, *, scroll: bool = False) -> str | None:
        try:
            from app.scrapers.playwright_pool import get_playwright_pool

            settings = get_settings()
            timeout_ms = int(max(self.timeout, settings.SCRAPER_PLAYWRIGHT_TIMEOUT) * 1000)
            return get_playwright_pool().fetch(url, timeout_ms=timeout_ms, human_scroll=scroll)
        except Exception as exc:
            logger.debug("Playwright fetch failed for %s: %s", url, exc)
            return None
