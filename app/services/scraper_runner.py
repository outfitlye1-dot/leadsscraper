"""Wire scraper jobs to the job store with live terminal logs."""

import threading
import time
from collections.abc import Callable

from fastapi import HTTPException

from app.database.database import SessionLocal
from app.models.user import User
from app.schemas.common import ScraperStartRequest, ScraperStartResponse
from app.services.all_in_one_scraper_service import AllInOneScraperService
from app.services.lead_service import LeadService
from app.services.scrape_suggest_service import ScrapeSuggestService
from app.services.scrape_cache_service import ScrapeCacheService
from app.utils.auto_query_rotation import lock_auto_internet_only, pick_auto_scrape_request
from app.services.scraper_job_store import scraper_job_store

ProgressCallback = Callable[[int, str, str], None]


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

    db = SessionLocal()
    metrics = ScrapeMetrics()
    scraper_job_store.bind_metrics(job_id, metrics)
    try:
        on_progress, on_log = _make_callbacks(job_id)
        scraper_job_store.update(
            job_id, status="running", progress=2, stage="init", message="Starting scraper..."
        )
        on_log("info", "init", "Job started")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            scraper_job_store.fail(job_id, "User not found")
            return

        if scraper_job_store.is_cancelled(job_id):
            scraper_job_store.update(job_id, status="cancelled", message="Cancelled before start")
            return

        cached = ScrapeCacheService(db).try_fulfill_from_cache(user_id, data)
        if cached:
            on_log("info", "cache", f"Using {cached.count} lead(s) from background cache")
            on_log("success", "done", cached.message)
            scraper_job_store.complete(job_id, cached.model_dump())
            delete_checkpoint(job_id)
            return

        on_log("info", "cache", "No matching cache — starting live scrape")
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
        scraper_job_store.complete(job_id, result.model_dump())
        delete_checkpoint(job_id)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        scraper_job_store.append_log(job_id, detail, level="error", stage="error")
        scraper_job_store.fail(job_id, detail)
    except Exception as exc:
        scraper_job_store.append_log(job_id, str(exc), level="error", stage="error")
        scraper_job_store.fail(job_id, str(exc))
    finally:
        db.close()


def start_scraper_job(user_id: int, data: ScraperStartRequest) -> str:
    if scraper_job_store.get_active_auto_job(user_id):
        raise HTTPException(
            status_code=409,
            detail="Auto scraping is running. Stop it before starting a manual scrape.",
        )
    if scraper_job_store.has_active_manual_job(user_id):
        raise HTTPException(
            status_code=409,
            detail="A manual scrape is already running. Wait for it to finish or refresh job status.",
        )
    job_id = scraper_job_store.create(user_id, mode="single")
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, user_id, data),
        daemon=True,
    )
    thread.start()
    return job_id


AUTO_SCRAPE_INTERVAL_SECONDS = 15


def _run_auto_job(
    job_id: str,
    user_id: int,
    data: ScraperStartRequest,
    interval_seconds: int = AUTO_SCRAPE_INTERVAL_SECONDS,
) -> None:
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

            job = scraper_job_store.get(job_id, user_id)
            stats_msg = (
                f"Round {iteration} done — kept {kept} with phone in Leads, removed {deleted} without contact. "
                f"Total kept: {job.auto_kept_total if job else kept}."
            )
            auto_log("success", "auto", stats_msg)
            if scraper_job_store.is_cancelled(job_id):
                scraper_job_store.update(job_id, progress=100, stage="done", message=stats_msg)
                break

            scraper_job_store.update(
                job_id,
                progress=0,
                stage="auto_wait",
                message=f"{stats_msg} Next scrape in {interval_seconds}s...",
            )
            for _ in range(interval_seconds):
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
) -> str:
    if scraper_job_store.get_active_auto_job(user_id):
        raise HTTPException(
            status_code=409,
            detail="Auto scraping is already running.",
        )
    if scraper_job_store.has_active_manual_job(user_id):
        raise HTTPException(
            status_code=409,
            detail="A manual scrape is already running. Wait for it to finish before starting auto scrape.",
        )

    db = SessionLocal()
    try:
        from app.utils.auto_query_rotation import prepare_auto_scrape_base

        profile = ScrapeSuggestService(db).get_brain_profile(user_id)
        data = prepare_auto_scrape_base(data, profile)
    finally:
        db.close()
    job_id = scraper_job_store.create(user_id, mode="auto")
    thread = threading.Thread(
        target=_run_auto_job,
        args=(job_id, user_id, data, interval_seconds),
        daemon=True,
    )
    thread.start()
    return job_id


def stop_auto_scraper_job(user_id: int) -> bool:
    job = scraper_job_store.get_active_auto_job(user_id)
    if not job:
        return False
    return scraper_job_store.request_cancel(job.job_id, user_id)
