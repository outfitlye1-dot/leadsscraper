import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait, FIRST_COMPLETED
from urllib.parse import urlparse

from app.core.config import get_settings
from app.scraper.metrics import ScrapeMetrics
from app.scraper.utils.workers import compute_crawl_workers
from app.scrapers.crawler_core import scrape_business_site
from app.scrapers.fetcher import PageFetcher
from app.scrapers.playwright_pool import playwright_session

logger = logging.getLogger(__name__)


class StreamingSiteCrawler:
    """
    Crawl seeds as they arrive from multi-engine discovery.
    Under high load, many crawl workers run in parallel while search continues.
    """

    def __init__(
        self,
        *,
        location: str,
        limit: int,
        crawl_seed_limit: int,
        workers: int,
        industry_hint: str | None = None,
        metrics: ScrapeMetrics | None = None,
        job_control: Callable[[], bool] | None = None,
        job_id: str | None = None,
    ):
        self.location = location
        self.limit = limit
        self.crawl_seed_limit = crawl_seed_limit
        self.workers = max(1, workers)
        self.industry_hint = industry_hint
        self.metrics = metrics
        self.job_control = job_control
        self.job_id = job_id

        self.seed_titles: dict[str, str] = {}
        self.seed_descriptions: dict[str, str] = {}
        self.results: list[dict] = []
        self.seen_hosts: set[str] = set()
        self.seen_urls: set[str] = set()
        self._queued_hosts: set[str] = set()
        self._lock = threading.Lock()
        self._aborted = threading.Event()
        self._submitted = 0
        self._started = False
        self._executor: ThreadPoolExecutor | None = None
        self._futures: set[Future] = set()
        self._pending_urls: list[str] = []
        self._pw_cm = None

    @property
    def submitted_count(self) -> int:
        return self._submitted

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def result_count(self) -> int:
        with self._lock:
            return len(self.results)

    def ensure_started(self) -> None:
        self.start()

    def flush(self) -> None:
        self._flush_pending()

    def abort(self) -> None:
        self._aborted.set()

    def _should_stop(self) -> bool:
        if self._aborted.is_set():
            return True
        if self.job_control and self.job_control():
            self._aborted.set()
            return True
        with self._lock:
            if len(self.results) >= self.limit:
                self._aborted.set()
                return True
        return False

    def _flush_pending(self) -> None:
        if not self._executor:
            return
        while True:
            with self._lock:
                if not self._pending_urls:
                    break
                url = self._pending_urls.pop(0)
            if self._should_stop():
                with self._lock:
                    self._pending_urls.clear()
                return
            fut = self._executor.submit(self._scrape_one, url)
            self._futures.add(fut)
        if self.metrics:
            with self._lock:
                submitted = self._submitted
                done = len(self.results)
            self.metrics.queue_size = max(0, submitted - done)

    def start(self) -> None:
        if self._started:
            self._flush_pending()
            return
        self._started = True
        settings = get_settings()
        # Only open Playwright when we will actually use it
        if settings.SCRAPER_ENABLE_PLAYWRIGHT and not settings.SCRAPER_FAST_MODE:
            self._pw_cm = playwright_session()
            self._pw_cm.__enter__()
        self._executor = ThreadPoolExecutor(max_workers=self.workers)
        if self.metrics:
            self.metrics.active_workers = self.workers
        logger.info(
            "Pipeline crawl LIVE: %s workers · target=%s · seed_cap=%s · playwright=%s",
            self.workers,
            self.limit,
            self.crawl_seed_limit,
            bool(self._pw_cm),
        )
        self._flush_pending()

    def add_seeds(self, items: list[dict], *, auto_start: bool = True) -> int:
        """Enqueue crawlable website seeds. Returns how many new URLs were accepted."""
        if self._should_stop():
            return 0
        accepted = 0
        for item in items:
            if self._should_stop():
                break
            url = (item.get("url") or "").strip()
            if not url:
                continue
            with self._lock:
                if self._submitted >= self.crawl_seed_limit:
                    break
                if url in self.seen_urls:
                    continue
                host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
                if host.startswith("www."):
                    host = host[4:]
                if not host or host in self._queued_hosts or host in self.seen_hosts:
                    continue
                self.seen_urls.add(url)
                self._queued_hosts.add(host)
                self.seed_titles[url] = item.get("title") or ""
                if item.get("description"):
                    self.seed_descriptions[url] = item["description"]
                self._submitted += 1
                self._pending_urls.append(url)
                accepted += 1

        if not accepted:
            return 0
        if self._started:
            self._flush_pending()
        elif auto_start:
            self.start()
        return accepted

    def _scrape_one(self, url: str) -> dict | None:
        if self._should_stop():
            return None
        settings = get_settings()
        host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        with self._lock:
            if host in self.seen_hosts or len(self.results) >= self.limit:
                return None

        # Fast internet path: HTTP only — Playwright was serializing all crawl workers
        use_pw = settings.SCRAPER_ENABLE_PLAYWRIGHT and not settings.SCRAPER_FAST_MODE
        fetcher = PageFetcher(
            timeout=min(settings.SCRAPER_TIMEOUT, 5.0 if settings.SCRAPER_FAST_MODE else 6.0),
            use_playwright=use_pw,
            metrics=self.metrics,
            job_control=self._should_stop,
        )
        item = scrape_business_site(
            fetcher,
            url,
            self.seed_titles.get(url),
            self.location,
            self.seed_descriptions.get(url),
            self.industry_hint,
            metrics=self.metrics,
        )
        if self._should_stop():
            return None
        if not item:
            if self.job_id:
                from app.services.scraper_job_store import scraper_job_store

                scraper_job_store.add_failed_url(self.job_id, url)
            return None

        with self._lock:
            if host in self.seen_hosts or len(self.results) >= self.limit or self._should_stop():
                return None
            self.seen_hosts.add(host)
            self.results.append(item)
            if self.metrics:
                self.metrics.queue_size = max(0, self._submitted - len(self.results))
        return item

    def drain(self, *, max_wait_seconds: float = 45.0) -> None:
        """Wait for in-flight crawl tasks (or abort / time out)."""
        if not self._executor:
            return
        pending = set(self._futures)
        deadline = time.monotonic() + max(5.0, max_wait_seconds)
        while pending:
            timed_out = time.monotonic() >= deadline
            if self._should_stop() or timed_out:
                logger.info(
                    "Pipeline crawl abort — cancelling %s tasks (timed_out=%s)",
                    len(pending),
                    timed_out,
                )
                for fut in pending:
                    fut.cancel()
                break
            done, pending = wait(pending, timeout=0.4, return_when=FIRST_COMPLETED)
            for future in done:
                self._futures.discard(future)
                try:
                    future.result()
                except Exception as exc:
                    logger.debug("Pipeline crawl task failed: %s", exc)
            with self._lock:
                if len(self.results) >= self.limit:
                    self._aborted.set()
                    for fut in pending:
                        fut.cancel()
                    break

    def close(self, *, max_wait_seconds: float = 30.0) -> list[dict]:
        try:
            self.drain(max_wait_seconds=max_wait_seconds)
        finally:
            if self._executor:
                self._executor.shutdown(wait=False, cancel_futures=True)
                self._executor = None
            if self._pw_cm is not None:
                try:
                    self._pw_cm.__exit__(None, None, None)
                except Exception:
                    pass
                self._pw_cm = None
            if self.metrics:
                self.metrics.active_workers = 0
                self.metrics.queue_size = 0
        return self.results[: self.limit]


def crawl_business_urls_parallel(
    seed_urls: list[str],
    seed_titles: dict[str, str],
    location: str,
    limit: int,
    crawl_seed_limit: int | None = None,
    seed_descriptions: dict[str, str] | None = None,
    industry_hint: str | None = None,
    metrics: ScrapeMetrics | None = None,
    job_control: Callable[[], bool] | None = None,
    job_id: str | None = None,
) -> list[dict]:
    if not seed_urls:
        return []

    settings = get_settings()
    max_seeds = crawl_seed_limit or max(int(limit * settings.SCRAPER_CRAWL_SEED_MULTIPLIER), limit + 12)
    urls = seed_urls[:max_seeds]
    workers = compute_crawl_workers(len(urls), limit)
    logger.info(
        "Parallel crawl starting: %s URLs divided across %s workers (target limit=%s)",
        len(urls),
        workers,
        limit,
    )

    crawler = StreamingSiteCrawler(
        location=location,
        limit=limit,
        crawl_seed_limit=max_seeds,
        workers=workers,
        industry_hint=industry_hint,
        metrics=metrics,
        job_control=job_control,
        job_id=job_id,
    )
    if metrics:
        metrics.inc("pages_discovered", len(urls))
    crawler.start()
    crawler.add_seeds(
        [
            {
                "url": url,
                "title": seed_titles.get(url, ""),
                "description": (seed_descriptions or {}).get(url),
            }
            for url in urls
        ]
    )
    return crawler.close()
