"""Dynamic worker pool sizing — more tasks ⇒ more parallel workers (capped)."""

from __future__ import annotations

from app.core.config import get_settings


def compute_parallel_workers(
    task_count: int,
    *,
    min_workers: int | None = None,
    max_workers: int | None = None,
) -> int:
    """Scale workers with backlog size. Divides work across more threads when busy."""
    settings = get_settings()
    floor = min_workers if min_workers is not None else settings.SCRAPER_MIN_WORKERS
    ceiling = max_workers if max_workers is not None else settings.SCRAPER_MAX_WORKERS
    if task_count <= 0:
        return floor

    scaled = max(floor, settings.SCRAPER_WORKERS, task_count // 2)
    if task_count >= 16:
        scaled = max(scaled, settings.SCRAPER_WORKERS + task_count // 3)
    if task_count >= 40:
        scaled = max(scaled, settings.SCRAPER_MAX_WORKERS - 2)

    return min(ceiling, scaled, task_count)


def compute_crawl_workers(url_count: int, target_limit: int) -> int:
    workload = max(url_count, target_limit * 2, 1)
    return compute_parallel_workers(workload)


def compute_search_workers(query_count: int) -> int:
    settings = get_settings()
    queries = max(query_count, 1)
    # Each query runs DDGS + Bing in parallel → 2 tasks per query
    task_estimate = queries * 2
    return min(settings.SCRAPER_SEARCH_MAX_WORKERS, compute_parallel_workers(task_estimate))


def compute_source_workers(active_sources: int) -> int:
    return max(1, min(active_sources, get_settings().SCRAPER_MAX_WORKERS))
