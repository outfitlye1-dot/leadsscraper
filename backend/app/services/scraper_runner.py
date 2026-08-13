"""Wire scraper jobs to the job store with live terminal logs."""

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from app.database.database import SessionLocal
from app.models.user import User
from app.schemas.common import ScraperStartRequest, ScraperStartResponse
from app.services.all_in_one_scraper_service import AllInOneScraperService
from app.services.lead_service import LeadService
from app.services.scrape_suggest_service import ScrapeSuggestService
from app.services.scrape_cache_service import ScrapeCacheService
from app.utils.auto_query_rotation import (
    keyword_rotation_pool,
    lock_auto_internet_only,
    pick_auto_scrape_request,
    pick_rotated_keyword,
)
from app.utils.scrape_defaults import cities_for_country, normalize_country_name
from app.services.scraper_job_store import scraper_job_store
from app.utils.host_limits import constrained_worker_cap, is_constrained_host
from app.utils.scrape_sources import ScrapeSourceMode
from app.utils.website_utils import WebsiteFilter

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[int, str, str], None]

# Single shared worker on Railway — nested pools + Playwright exhaust OS threads
_SCRAPE_EXECUTOR = ThreadPoolExecutor(
    max_workers=1 if is_constrained_host() else 2,
    thread_name_prefix="scrape-job",
)


def _queue_job(fn, *args, **kwargs) -> None:
    """Submit to the shared pool; re-raise RuntimeError with a clear message."""
    try:
        _SCRAPE_EXECUTOR.submit(fn, *args, **kwargs)
    except RuntimeError as exc:
        if "can't start new thread" in str(exc).lower() or "thread" in str(exc).lower():
            raise RuntimeError(
                "Server is out of threads/memory. Restart the Railway backend, "
                "then scrape with limit 3–5 (Maps only)."
            ) from exc
        raise


def _make_callbacks(job_id: str) -> tuple[ProgressCallback, Callable[[str, str, str], None]]:
    def on_progress(percent: int, stage: str, message: str) -> None:
        scraper_job_store.update(job_id, progress=percent, stage=stage, message=message)

    def on_log(level: str, stage: str, text: str) -> None:
        scraper_job_store.append_log(job_id, text, level=level, stage=stage)

    return on_progress, on_log


def _run_job(job_id: str, user_id: int, data: ScraperStartRequest) -> None:
    from app.core.config import get_settings
    from app.scraper.metrics import ScrapeMetrics
    from app.scrapers.checkpoint import delete_checkpoint, save_checkpoint

    scraper_job_store.update(
        job_id, status="running", progress=1, stage="init", message="Starting scraper..."
    )
    db = None
    metrics = ScrapeMetrics()
    scraper_job_store.bind_metrics(job_id, metrics)
    try:
        on_progress, on_log = _make_callbacks(job_id)
        on_log("info", "init", "Job started")
        scraper_job_store.begin_round(
            job_id,
            1,
            label=f"{(data.keyword or '').strip()} · {(data.location or '').strip()}".strip(" ·"),
        )
        scraper_job_store.update(job_id, progress=3, stage="init", message="Loading account...")
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            scraper_job_store.fail(job_id, "User not found")
            return

        if scraper_job_store.is_cancelled(job_id):
            scraper_job_store.update(job_id, status="cancelled", message="Cancelled before start")
            return

        # Cache lookup (Postgres is fine inline; avoid nested thread pools on Railway)
        scraper_job_store.update(job_id, progress=4, stage="init", message="Checking cache...")
        cached = None
        try:
            cached = ScrapeCacheService(db).try_fulfill_from_cache(user_id, data)
        except Exception as cache_exc:
            on_log("warn", "cache", f"Cache skipped: {cache_exc}")
            cached = None

        if cached:
            on_log("info", "cache", f"Using {cached.count} lead(s) from background cache")
            on_log("success", "done", cached.message)
            scraper_job_store.finish_round(
                job_id,
                1,
                scraped=cached.count,
                kept=cached.count,
                deleted=0,
            )
            scraper_job_store.complete(job_id, cached.model_dump())
            delete_checkpoint(job_id)
            return

        on_log("info", "cache", "No matching cache — starting live scrape")
        scraper_job_store.update(
            job_id, progress=5, stage="init", message="Starting live scrape..."
        )
        # Release any held SQLite lock before long network I/O
        try:
            if db.in_transaction():
                db.commit()
        except Exception:
            db.rollback()
        result = AllInOneScraperService(db).run(
            user,
            data,
            on_progress=on_progress,
            on_log=on_log,
            job_id=job_id,
            metrics=metrics,
        )
        if scraper_job_store.is_cancelled(job_id):
            scraper_job_store.update(job_id, status="cancelled", message="Scrape cancelled")
            if get_settings().SCRAPER_CHECKPOINT_ENABLED:
                save_checkpoint(job_id, {"partial_result": result.model_dump(), "cancelled": True})
            return
        on_log("success", "done", result.message or f"Done — {result.count} leads saved")
        scraper_job_store.finish_round(
            job_id,
            1,
            scraped=result.count,
            kept=result.count,
            deleted=0,
        )
        scraper_job_store.complete(job_id, result.model_dump())
        delete_checkpoint(job_id)
    except HTTPException as exc:
        if scraper_job_store.is_cancelled(job_id):
            scraper_job_store.update(job_id, status="cancelled", message="Stopped")
            return
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        scraper_job_store.append_log(job_id, detail, level="error", stage="error")
        scraper_job_store.fail(job_id, detail)
    except Exception as exc:
        if scraper_job_store.is_cancelled(job_id):
            scraper_job_store.update(job_id, status="cancelled", message="Stopped")
            return
        scraper_job_store.append_log(job_id, str(exc), level="error", stage="error")
        scraper_job_store.fail(job_id, str(exc))
    finally:
        if db is not None:
            db.close()


def start_scraper_job(user_id: int, data: ScraperStartRequest) -> str:
    if scraper_job_store.get_active_auto_job(user_id):
        raise HTTPException(
            status_code=409,
            detail="Auto scraping is running. Stop auto scrape before starting a manual scrape.",
        )
    # Free CPU/DB for the user-facing scrape
    try:
        from app.services.background_scrape_runner import stop_background_scraper

        stop_background_scraper(user_id)
    except Exception:
        pass
    # Replace any stuck/running manual job so clicking Start always works
    replaced = scraper_job_store.cancel_active_manual_jobs(user_id)
    if replaced:
        logger.info("Replaced active manual scrape(s) %s for user %s", replaced, user_id)

    job_id = scraper_job_store.create(user_id, mode="single")
    # Always return job_id — never 500 after create (browser shows Network Error on bare 500/CORS)
    try:
        scraper_job_store.update(
            job_id,
            status="running",
            progress=1,
            stage="init",
            message="Queued…",
        )
        _queue_job(_run_job, job_id, user_id, data)
    except Exception as exc:
        logger.exception("Failed to queue scrape job %s: %s", job_id, exc)
        msg = str(exc)
        if "thread" in msg.lower() or "memory" in msg.lower():
            msg = (
                "Server is out of threads/memory. Restart the Railway backend, "
                "then retry with limit 3–5."
            )
        scraper_job_store.fail(job_id, msg)
    return job_id


AUTO_SCRAPE_INTERVAL_SECONDS = 15
AUTO_SCRAPE_EMPTY_INTERVAL_SECONDS = 5


def _scrape_one_city(
    user_id: int,
    job_id: str,
    base: ScraperStartRequest,
    city_location: str,
    agent_label: str,
    agent_id: str,
) -> tuple[str, int, int, int]:
    """Run one city scrape in its own DB session. Returns (city, scraped, kept, deleted)."""
    db = SessionLocal()
    keyword = (base.keyword or "").strip() or "local business"
    city_short = city_location.split(",")[0].strip()
    try:
        if scraper_job_store.is_cancelled(job_id):
            scraper_job_store.update_agent(
                job_id,
                agent_id,
                status="idle",
                message="Cancelled",
            )
            return city_location, 0, 0, 0
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            scraper_job_store.update_agent(
                job_id, agent_id, status="failed", message="User not found"
            )
            return city_location, 0, 0, 0

        scraper_job_store.update_agent(
            job_id,
            agent_id,
            status="running",
            keyword=keyword,
            city=city_short,
            message="Opening Google Maps…",
            kept=0,
            scraped=0,
        )

        scrape_data = base.model_copy(
            update={
                "location": city_location,
                "search_query": f"{keyword} {city_short}",
                "limit": min(int(base.limit or 15), 15),
                "scrape_source": ScrapeSourceMode.google_maps,
                "website_filter": WebsiteFilter.without_website,
                "enrich_contacts": False,
                "auto_generate_whatsapp": False,
                "include_meta_ads": False,
            }
        )

        def on_progress(percent: int, stage: str, message: str) -> None:
            scraper_job_store.update_agent(
                job_id,
                agent_id,
                status="running",
                keyword=keyword,
                city=city_short,
                message=message,
            )
            scraper_job_store.update(
                job_id,
                progress=percent,
                stage=stage,
                message=f"{agent_label} · {city_short}: {message}",
            )

        def on_log(level: str, stage: str, text: str) -> None:
            scraper_job_store.append_log(
                job_id, f"[{agent_label}/{city_short}] {text}", level=level, stage=stage
            )

        result = AllInOneScraperService(db).run(
            user,
            scrape_data,
            on_progress=on_progress,
            on_log=on_log,
        )
        lead_service = LeadService(db)
        kept, deleted = lead_service.cleanup_non_phone_leads_by_ids(
            user_id, result.saved_lead_ids
        )
        scraper_job_store.update_agent(
            job_id,
            agent_id,
            status="done",
            keyword=keyword,
            city=city_short,
            message=f"Kept {kept} phone leads",
            kept=kept,
            scraped=result.count,
        )
        return city_location, result.count, kept, deleted
    except Exception as exc:
        logger.warning("Country agent %s failed for %s: %s", agent_label, city_location, exc)
        scraper_job_store.update_agent(
            job_id,
            agent_id,
            status="failed",
            keyword=keyword,
            city=city_short,
            message=str(exc)[:160],
        )
        scraper_job_store.append_log(
            job_id,
            f"[{agent_label}] {city_location} failed: {exc}",
            level="error",
            stage="auto",
        )
        return city_location, 0, 0, 0
    finally:
        db.close()


def _run_country_auto_job(
    job_id: str,
    user_id: int,
    data: ScraperStartRequest,
    country: str,
    parallel_agents: int = 2,
    interval_seconds: int = AUTO_SCRAPE_INTERVAL_SECONDS,
) -> None:
    """Multi-agent auto: rotate cities + keywords with parallel Playwright scrapers."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cities = cities_for_country(country)
    if not cities:
        scraper_job_store.fail(job_id, f"No cities configured for country: {country}")
        return

    brain_profile: dict | None = None
    try:
        db = SessionLocal()
        try:
            brain_profile = ScrapeSuggestService(db).get_brain_profile(user_id)
        finally:
            db.close()
    except Exception:
        brain_profile = None

    kw_pool = keyword_rotation_pool(
        data.keyword or "",
        brain_profile,
        rotate=bool(getattr(data, "rotate_keywords", True)),
    )
    agents = max(1, min(int(parallel_agents or 3), constrained_worker_cap(), 5, len(cities)))
    if is_constrained_host():
        agents = 1
    rotate_on = len(kw_pool) > 1
    scraper_job_store.update(
        job_id,
        status="running",
        progress=2,
        stage="auto",
        message=(
            f"Country auto · {country} · {agents} agents · {len(cities)} cities · "
            + ("rotating keywords" if rotate_on else f"fixed keyword “{kw_pool[0]}”")
        ),
    )
    scraper_job_store.append_log(
        job_id,
        (
            f"Country auto started — {country}, {len(cities)} cities, {agents} parallel agents, "
            + (
                f"{len(kw_pool)} keywords in rotation"
                if rotate_on
                else f"keyword locked: {kw_pool[0]}"
            )
        ),
        level="info",
        stage="auto",
    )

    city_index = 0
    wave = 0
    while not scraper_job_store.is_cancelled(job_id):
        wave += 1
        scraper_job_store.set_iteration(job_id, wave)
        batch: list[str] = []
        for i in range(agents):
            batch.append(cities[(city_index + i) % len(cities)])
        city_index = (city_index + agents) % len(cities)

        wave_keywords: list[str] = []
        roster = []
        for i, city in enumerate(batch):
            city_short = city.split(",")[0].strip()
            kw = pick_rotated_keyword(kw_pool, (wave - 1) * agents + i)
            wave_keywords.append(kw)
            roster.append(
                {
                    "id": f"agent-{i + 1}",
                    "label": f"Agent {i + 1}",
                    "keyword": kw,
                    "city": city_short,
                    "status": "queued",
                    "message": "Waiting for browser…",
                    "kept": 0,
                    "scraped": 0,
                }
            )
        scraper_job_store.set_agents(job_id, roster)
        wave_label = ", ".join(f"{kw} @ {city.split(',')[0].strip()}" for kw, city in zip(wave_keywords, batch))
        scraper_job_store.begin_round(job_id, wave, label=wave_label)

        scraper_job_store.update(
            job_id,
            progress=5,
            stage="auto",
            message=(
                f"Wave {wave} — "
                + ", ".join(
                    f"{pick_rotated_keyword(kw_pool, (wave - 1) * agents + i)}@"
                    f"{city.split(',')[0]}"
                    for i, city in enumerate(batch)
                )
            ),
        )
        scraper_job_store.append_log(
            job_id,
            f"Wave {wave} keywords: {', '.join(wave_keywords)}",
            level="info",
            stage="auto",
        )

        wave_kept = 0
        wave_deleted = 0
        wave_scraped = 0
        with ThreadPoolExecutor(max_workers=agents) as executor:
            futures = {}
            for i, city in enumerate(batch):
                kw = wave_keywords[i]
                city_short = city.split(",")[0].strip()
                agent_data = data.model_copy(
                    update={
                        "keyword": kw,
                        "search_query": f"{kw} {city_short}",
                        "location": city,
                    }
                )
                fut = executor.submit(
                    _scrape_one_city,
                    user_id,
                    job_id,
                    agent_data,
                    city,
                    f"Agent {i + 1}",
                    f"agent-{i + 1}",
                )
                futures[fut] = city
            for fut in as_completed(futures):
                if scraper_job_store.is_cancelled(job_id):
                    break
                city, scraped, kept, deleted = fut.result()
                wave_scraped += scraped
                wave_kept += kept
                wave_deleted += deleted
                scraper_job_store.add_auto_stats(
                    job_id, scraped=scraped, kept=kept, deleted=deleted
                )
                scraper_job_store.append_log(
                    job_id,
                    f"{city.split(',')[0]} done — kept {kept}, removed {deleted}",
                    level="success",
                    stage="auto",
                )

        scraper_job_store.finish_round(
            job_id,
            wave,
            scraped=wave_scraped,
            kept=wave_kept,
            deleted=wave_deleted,
        )
        job = scraper_job_store.get(job_id, user_id)
        stats_msg = (
            f"Wave {wave} done — kept {wave_kept} phones this wave "
            f"(total kept {job.auto_kept_total if job else wave_kept})."
        )
        if scraper_job_store.is_cancelled(job_id):
            scraper_job_store.update(job_id, progress=100, stage="done", message=stats_msg)
            break

        wait_seconds = (
            AUTO_SCRAPE_EMPTY_INTERVAL_SECONDS if wave_kept == 0 else min(interval_seconds, 8)
        )
        for agent in roster:
            scraper_job_store.update_agent(
                job_id,
                agent["id"],
                status="waiting",
                message=f"Next wave in {wait_seconds}s…",
            )
        scraper_job_store.update(
            job_id,
            progress=0,
            stage="auto_wait",
            message=f"{stats_msg} Next cities/keywords in {wait_seconds}s...",
        )
        for _ in range(wait_seconds):
            if scraper_job_store.is_cancelled(job_id):
                break
            time.sleep(1)

    job = scraper_job_store.get(job_id, user_id)
    scraper_job_store.complete(
        job_id,
        {
            "success": True,
            "count": job.auto_kept_total if job else 0,
            "message": (
                f"Country auto stopped after {wave} wave(s) across {country}. "
                f"Kept {job.auto_kept_total if job else 0} phone leads, "
                f"removed {job.auto_deleted_total if job else 0} without phone."
            ),
            "saved_lead_ids": [],
        },
    )


def _run_auto_job(
    job_id: str,
    user_id: int,
    data: ScraperStartRequest,
    interval_seconds: int = AUTO_SCRAPE_INTERVAL_SECONDS,
    *,
    country: str | None = None,
    parallel_agents: int = 2,
) -> None:
    if country:
        canonical = normalize_country_name(country)
        if canonical:
            _run_country_auto_job(
                job_id,
                user_id,
                data,
                canonical,
                parallel_agents=parallel_agents,
                interval_seconds=interval_seconds,
            )
            return
        scraper_job_store.append_log(
            job_id,
            f"Unknown country {country!r} — falling back to single-location auto",
            level="warning",
            stage="auto",
        )

    db = SessionLocal()
    try:
        on_progress, on_log = _make_callbacks(job_id)
        scraper_job_store.update(
            job_id,
            status="running",
            progress=2,
            stage="auto",
            message="Auto scraping started — round 1...",
        )
        on_log("info", "auto", "Auto mode started — phone leads only")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            scraper_job_store.fail(job_id, "User not found")
            return

        lead_service = LeadService(db)
        suggest_service = ScrapeSuggestService(db)
        brain_profile = suggest_service.get_brain_profile(user.id)
        iteration = 0

        while not scraper_job_store.is_cancelled(job_id):
            iteration += 1
            scraper_job_store.set_iteration(job_id, iteration)

            scrape_data, query_label = pick_auto_scrape_request(
                data, brain_profile, iteration
            )
            scrape_data = lock_auto_internet_only(
                scrape_data.model_copy(update={"auto_generate_whatsapp": False})
            )
            scraper_job_store.begin_round(job_id, iteration, label=query_label)

            def auto_progress(percent: int, stage: str, message: str) -> None:
                full = f"Round {iteration} [{query_label}]: {message}"
                scraper_job_store.update(
                    job_id, progress=percent, stage=stage, message=full
                )
                scraper_job_store.append_log(job_id, full, level="info", stage=stage)

            def auto_log(level: str, stage: str, text: str) -> None:
                scraper_job_store.append_log(
                    job_id, f"[{query_label}] {text}", level=level, stage=stage
                )

            scraper_job_store.update(
                job_id,
                progress=1,
                stage="auto",
                message=f"Round {iteration} — {query_label}",
            )
            auto_log("info", "auto", f"Round {iteration} · query: {query_label}")
            try:
                cached = ScrapeCacheService(db).try_fulfill_from_cache(user_id, scrape_data)
                if cached:
                    auto_log(
                        "info",
                        "cache",
                        f"Using {cached.count} lead(s) from database cache",
                    )
                    kept, deleted = lead_service.cleanup_non_phone_leads_by_ids(
                        user_id, cached.saved_lead_ids
                    )
                    scraper_job_store.add_auto_stats(
                        job_id, scraped=cached.count, kept=kept, deleted=deleted
                    )
                    scraper_job_store.finish_round(
                        job_id,
                        iteration,
                        scraped=cached.count,
                        kept=kept,
                        deleted=deleted,
                    )
                    auto_log("success", "cache", cached.message)
                    if scraper_job_store.is_cancelled(job_id):
                        break
                    scraper_job_store.update(
                        job_id,
                        progress=0,
                        stage="auto_wait",
                        message=f"Cache round {iteration} done. Next in {interval_seconds}s...",
                    )
                    for _ in range(interval_seconds):
                        if scraper_job_store.is_cancelled(job_id):
                            break
                        time.sleep(1)
                    continue

                auto_log("info", "cache", "No database cache — starting live scrape")
                result = AllInOneScraperService(db).run(
                    user,
                    scrape_data,
                    on_progress=auto_progress,
                    on_log=auto_log,
                )
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                scraper_job_store.fail(job_id, detail)
                return
            except Exception as exc:
                scraper_job_store.fail(job_id, str(exc))
                return

            kept, deleted = lead_service.cleanup_non_phone_leads_by_ids(
                user_id, result.saved_lead_ids
            )
            scraper_job_store.add_auto_stats(
                job_id, scraped=result.count, kept=kept, deleted=deleted
            )
            scraper_job_store.finish_round(
                job_id,
                iteration,
                scraped=result.count,
                kept=kept,
                deleted=deleted,
            )

            job = scraper_job_store.get(job_id, user_id)
            stats_msg = (
                f"Round {iteration} done — kept {kept} with phone in Leads, removed {deleted} without contact. "
                f"Total kept: {job.auto_kept_total if job else kept}."
            )
            auto_log("success", "auto", stats_msg)
            if scraper_job_store.is_cancelled(job_id):
                scraper_job_store.update(job_id, progress=100, stage="done", message=stats_msg)
                break

            wait_seconds = (
                AUTO_SCRAPE_EMPTY_INTERVAL_SECONDS
                if kept == 0
                else interval_seconds
            )
            scraper_job_store.update(
                job_id,
                progress=0,
                stage="auto_wait",
                message=f"{stats_msg} Next scrape in {wait_seconds}s...",
            )
            for _ in range(wait_seconds):
                if scraper_job_store.is_cancelled(job_id):
                    break
                time.sleep(1)

        job = scraper_job_store.get(job_id, user_id)
        scraper_job_store.complete(
            job_id,
            {
                "success": True,
                "count": job.auto_kept_total if job else 0,
                "message": (
                    f"Auto scraping stopped after {iteration} round(s). "
                    f"Kept {job.auto_kept_total if job else 0} phone leads, "
                    f"removed {job.auto_deleted_total if job else 0} without phone."
                ),
                "saved_lead_ids": [],
            },
        )
    finally:
        db.close()


def start_auto_scraper_job(
    user_id: int,
    data: ScraperStartRequest,
    interval_seconds: int = AUTO_SCRAPE_INTERVAL_SECONDS,
    *,
    country: str | None = None,
    parallel_agents: int = 2,
) -> str:
    # Free CPU/DB for country agents
    try:
        from app.services.background_scrape_runner import stop_background_scraper

        stop_background_scraper(user_id)
    except Exception:
        pass
    # Replace any stuck/running auto job so clicking Auto always works
    replaced_auto = scraper_job_store.cancel_active_auto_jobs(user_id)
    if replaced_auto:
        logger.info("Replaced active auto scrape(s) %s for user %s", replaced_auto, user_id)
    # Also free a stuck manual scrape so auto isn't blocked after a refresh
    replaced_manual = scraper_job_store.cancel_active_manual_jobs(
        user_id, message="Stopped so auto scrape can start"
    )
    if replaced_manual:
        logger.info("Replaced active manual scrape(s) %s for user %s", replaced_manual, user_id)

    db = SessionLocal()
    try:
        from app.utils.auto_query_rotation import prepare_auto_scrape_base

        profile = ScrapeSuggestService(db).get_brain_profile(user_id)
        data = prepare_auto_scrape_base(data, profile)
    finally:
        db.close()

    # Prefer explicit country; else try to infer from location
    resolved_country = normalize_country_name(country)
    if not resolved_country and data.location:
        # "London, United Kingdom" → United Kingdom
        if "," in data.location:
            resolved_country = normalize_country_name(data.location.split(",")[-1].strip())
        else:
            resolved_country = normalize_country_name(data.location)

    job_id = scraper_job_store.create(user_id, mode="auto")
    agents = 1 if is_constrained_host() else max(1, min(int(parallel_agents or 2), constrained_worker_cap()))
    try:
        scraper_job_store.update(
            job_id,
            status="running",
            progress=1,
            stage="auto",
            message="Queued auto scrape…",
        )
        _queue_job(
            _run_auto_job,
            job_id,
            user_id,
            data,
            interval_seconds,
            country=resolved_country,
            parallel_agents=agents,
        )
    except Exception as exc:
        logger.exception("Failed to queue auto scrape %s: %s", job_id, exc)
        scraper_job_store.fail(
            job_id,
            str(exc)
            if "thread" in str(exc).lower() or "memory" in str(exc).lower()
            else (
                "Server could not start auto scrape (out of threads/memory). "
                "Restart Railway and try again."
            ),
        )
    return job_id


def stop_auto_scraper_job(user_id: int) -> bool:
    cancelled = scraper_job_store.cancel_active_auto_jobs(
        user_id, message="Stopped"
    )
    return bool(cancelled)
