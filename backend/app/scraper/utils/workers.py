"""Dynamic worker pool sizing — scales up under high load, stays bounded for reliability."""

from __future__ import annotations

from app.core.config import get_settings


def _target_workers() -> int:
    settings = get_settings()
    return max(1, min(settings.SCRAPER_WORKERS, settings.SCRAPER_MAX_WORKERS))


def compute_parallel_workers(
    task_count: int,
    *,
    min_workers: int | None = None,
    max_workers: int | None = None,
) -> int:
    """Scale workers with backlog — high load keeps the full pool busy."""
    settings = get_settings()
    target = _target_workers()
    if max_workers is not None:
        target = min(target, max_workers)
    if min_workers is not None:
        target = max(min_workers, target)
    if task_count <= 0:
        return max(1, min_workers or settings.SCRAPER_MIN_WORKERS)
    return target


def compute_crawl_workers(url_count: int, target_limit: int) -> int:
    """
    Crawl pool for internet sites.
    Playwright is effectively limited — keep crawl workers modest so jobs finish.
    """
    settings = get_settings()
    backlog = max(url_count, target_limit, 1)
    # Cap hard: too many workers serialize on Playwright and starve the job
    hard_cap = 8 if settings.SCRAPER_FAST_MODE else 12
    hard_cap = min(hard_cap, _target_workers())
    if backlog >= 10:
        return hard_cap
    return max(settings.SCRAPER_MIN_WORKERS, min(hard_cap, max(backlog, 4)))


def compute_search_workers(job_count: int) -> int:
    """
    Search discovery pool across engines.
    Keep modest — DDGS alone fans out many HTTP calls.
    """
    settings = get_settings()
    ceiling = min(
        max(settings.SCRAPER_SEARCH_MAX_WORKERS, settings.SCRAPER_WORKERS),
        settings.SCRAPER_MAX_WORKERS or 40,
        12 if settings.SCRAPER_FAST_MODE else 20,
    )
    jobs = max(job_count, 1)
    if jobs >= 6:
        return max(1, ceiling)
    return max(1, min(ceiling, max(jobs, settings.SCRAPER_MIN_WORKERS)))


def compute_source_workers(active_sources: int) -> int:
    return max(1, min(active_sources, get_settings().SCRAPER_MAX_WORKERS))
