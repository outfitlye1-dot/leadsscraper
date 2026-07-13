import logging
from typing import Any

from app.scraper.metrics import ScrapeMetrics
from app.scrapers.parallel_crawler import crawl_business_urls_parallel

logger = logging.getLogger(__name__)


def run_business_spider(
    seed_urls: list[str],
    seed_titles: dict[str, str],
    location: str,
    limit: int,
    timeout: int = 180,
    crawl_seed_limit: int | None = None,
    seed_descriptions: dict[str, str] | None = None,
    industry_hint: str | None = None,
    metrics: ScrapeMetrics | None = None,
    job_control=None,
    job_id: str | None = None,
) -> list[dict[str, Any]]:
    """Fast parallel crawl (replaces slow Scrapy subprocess)."""
    _ = timeout
    return crawl_business_urls_parallel(
        seed_urls,
        seed_titles,
        location,
        limit,
        crawl_seed_limit=crawl_seed_limit,
        seed_descriptions=seed_descriptions,
        industry_hint=industry_hint,
        metrics=metrics,
        job_control=job_control,
        job_id=job_id,
    )
