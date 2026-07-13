import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.config import get_settings
from app.scraper.metrics import ScrapeMetrics
from app.scraper.utils.workers import compute_crawl_workers
from app.scrapers.crawler_core import scrape_business_site
from app.scrapers.fetcher import PageFetcher
from app.scrapers.playwright_pool import playwright_session

logger = logging.getLogger(__name__)


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

    if metrics:
        metrics.inc("pages_discovered", len(urls))
        metrics.queue_size = len(urls)
        metrics.active_workers = workers

    results: list[dict] = []
    seen_hosts: set[str] = set()
    results_lock = threading.Lock()

    def _scrape_one(url: str) -> dict | None:
        if job_control and job_control():
            return None
        from urllib.parse import urlparse

        host = urlparse(url).netloc.lower()
        with results_lock:
            if host in seen_hosts:
                return None
            if len(results) >= limit:
                return None

        fetcher = PageFetcher(
            timeout=settings.SCRAPER_TIMEOUT,
            use_playwright=settings.SCRAPER_ENABLE_PLAYWRIGHT,
            metrics=metrics,
            job_control=job_control,
        )
        item = scrape_business_site(
            fetcher,
            url,
            seed_titles.get(url),
            location,
            (seed_descriptions or {}).get(url),
            industry_hint,
            metrics=metrics,
        )
        if not item:
            if job_id:
                from app.services.scraper_job_store import scraper_job_store

                scraper_job_store.add_failed_url(job_id, url)
            return None

        with results_lock:
            if host in seen_hosts or len(results) >= limit:
                return None
            seen_hosts.add(host)
            results.append(item)
            if metrics:
                metrics.queue_size = max(0, len(urls) - len(seen_hosts))
        return item

    with playwright_session():
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_scrape_one, url) for url in urls]
            for future in as_completed(futures):
                if job_control and job_control():
                    for pending in futures:
                        pending.cancel()
                    break
                try:
                    future.result()
                except Exception as exc:
                    logger.debug("Parallel crawl task failed: %s", exc)
                with results_lock:
                    if len(results) >= limit:
                        for pending in futures:
                            pending.cancel()
                        break

    if metrics:
        metrics.active_workers = 0
        metrics.queue_size = 0

    return results[:limit]
