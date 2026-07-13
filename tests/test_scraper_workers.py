from app.scraper.utils.workers import (
    compute_crawl_workers,
    compute_parallel_workers,
    compute_search_workers,
)


def test_compute_parallel_workers_scales_with_tasks():
    few = compute_parallel_workers(4)
    many = compute_parallel_workers(40)
    assert many >= few
    assert many <= 24


def test_compute_crawl_workers_increases_for_large_batches():
    small = compute_crawl_workers(5, 10)
    large = compute_crawl_workers(50, 25)
    assert large >= small


def test_compute_search_workers_scales_with_queries():
    one = compute_search_workers(1)
    five = compute_search_workers(5)
    assert five >= one
