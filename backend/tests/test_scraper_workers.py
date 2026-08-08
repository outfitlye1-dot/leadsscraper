from app.core.config import get_settings
from app.scraper.utils.workers import (
    compute_crawl_workers,
    compute_parallel_workers,
    compute_search_workers,
)


def test_compute_parallel_workers_targets_configured_pool():
    settings = get_settings()
    few = compute_parallel_workers(4)
    many = compute_parallel_workers(40)
    assert few == settings.SCRAPER_WORKERS
    assert many == settings.SCRAPER_WORKERS
    assert many <= settings.SCRAPER_MAX_WORKERS


def test_compute_crawl_workers_caps_for_reliability():
    settings = get_settings()
    large = compute_crawl_workers(50, 25)
    assert large <= 12
    assert large <= settings.SCRAPER_WORKERS
    small = compute_crawl_workers(3, 5)
    assert 1 <= small <= 12


def test_compute_search_workers_scales_under_multi_engine_load():
    settings = get_settings()
    one = compute_search_workers(1)
    assert one >= 1
    many = compute_search_workers(24)
    assert many <= 20
    assert many <= max(settings.SCRAPER_SEARCH_MAX_WORKERS, settings.SCRAPER_WORKERS)
