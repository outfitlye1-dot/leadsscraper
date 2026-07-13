"""Silent background scraper — collects leads while the user stays logged in."""

from __future__ import annotations

import logging
import threading
import time

from fastapi import HTTPException

from app.database.database import SessionLocal
from app.models.user import User
from app.schemas.common import ScraperStartRequest
from app.services.all_in_one_scraper_service import AllInOneScraperService
from app.services.background_scrape_store import (
    BACKGROUND_ROUND_SECONDS,
    background_scrape_store,
)
from app.services.scrape_suggest_service import ScrapeSuggestService
from app.services.scraper_job_store import scraper_job_store
from app.utils.auto_query_rotation import pick_background_scrape_request
from app.utils.scrape_defaults import DEFAULT_SCRAPE_LOCATION
from app.utils.website_utils import WebsiteFilter

logger = logging.getLogger(__name__)

BACKGROUND_LIMIT = 25


def _user_has_running_job(user_id: int) -> bool:
    return scraper_job_store.has_active_scrape_job(user_id)


def _background_loop(user_id: int, stop_event: threading.Event) -> None:
    background_scrape_store.mark_running(user_id)
    background_scrape_store.append_log(
        user_id, "Background scraper started", level="success", stage="init"
    )
    iteration = 0
    waiting_for_manual = False
    try:
        while not stop_event.is_set():
            if not background_scrape_store.is_session_alive(user_id):
                background_scrape_store.append_log(
                    user_id, "Session ended — stopping", level="warn", stage="idle"
                )
                break
            if _user_has_running_job(user_id):
                if not waiting_for_manual:
                    background_scrape_store.append_log(
                        user_id,
                        "Paused — manual scrape is running",
                        level="warn",
                        stage="idle",
                    )
                    waiting_for_manual = True
                background_scrape_store.update_progress(
                    user_id, 0, "idle", "Waiting for manual scrape to finish..."
                )
                time.sleep(8)
                continue
            waiting_for_manual = False

            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    break

                suggest = ScrapeSuggestService(db)
                profile = suggest.get_brain_profile(user_id)
                base = ScraperStartRequest(
                    keyword="restaurant",
                    location=DEFAULT_SCRAPE_LOCATION,
                    limit=BACKGROUND_LIMIT,
                    website_filter=WebsiteFilter.all,
                    enrich_contacts=True,
                    only_verified_contacts=False,
                    auto_generate_whatsapp=False,
                )

                iteration += 1
                scrape_data, query_label = pick_background_scrape_request(
                    base, profile, iteration
                )
                scrape_data = scrape_data.model_copy(
                    update={
                        "limit": BACKGROUND_LIMIT,
                        "website_filter": WebsiteFilter.all,
                        "only_verified_contacts": False,
                        "auto_generate_whatsapp": False,
                    }
                )

                background_scrape_store.append_log(
                    user_id,
                    f"Round {iteration}: {query_label}",
                    level="info",
                    stage="init",
                )
                background_scrape_store.update_progress(
                    user_id, 5, "init", f"Round {iteration} — {query_label}"
                )

                try:
                    db.commit()
                except Exception:
                    db.rollback()

                def on_progress(percent: int, stage: str, message: str) -> None:
                    background_scrape_store.update_progress(user_id, percent, stage, message)

                def on_log(level: str, stage: str, text: str) -> None:
                    background_scrape_store.append_log(
                        user_id, text, level=level, stage=stage
                    )

                service = AllInOneScraperService(db)
                result = service.run(
                    user,
                    scrape_data,
                    on_progress=on_progress,
                    on_log=on_log,
                    background=True,
                )
                if result.count:
                    background_scrape_store.record_round(
                        user_id, saved=result.count, query_label=query_label
                    )
                    background_scrape_store.append_log(
                        user_id,
                        f"Saved {result.count} lead(s) · session total {background_scrape_store.get_status(user_id)['total_saved']}",
                        level="success",
                        stage="save",
                    )
                else:
                    background_scrape_store.append_log(
                        user_id,
                        result.message or "No new leads this round",
                        level="warn",
                        stage="save",
                    )
                background_scrape_store.update_progress(
                    user_id,
                    0,
                    "idle",
                    f"Idle — next round in {BACKGROUND_ROUND_SECONDS}s",
                )
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                background_scrape_store.append_log(
                    user_id, f"Skipped: {detail}", level="warn", stage="error"
                )
                logger.debug("Background scrape skipped: %s", detail)
            except Exception as exc:
                background_scrape_store.append_log(
                    user_id, f"Error: {exc}", level="error", stage="error"
                )
                logger.warning("Background scrape error for user %s: %s", user_id, exc)
            finally:
                db.close()

            background_scrape_store.append_log(
                user_id,
                f"Waiting {BACKGROUND_ROUND_SECONDS}s until next round...",
                level="info",
                stage="idle",
            )
            for _ in range(BACKGROUND_ROUND_SECONDS):
                if stop_event.is_set() or not background_scrape_store.is_session_alive(user_id):
                    break
                time.sleep(1)
    finally:
        background_scrape_store.mark_stopped(user_id)
        background_scrape_store.clear_thread(user_id)
        background_scrape_store.append_log(
            user_id, "Background scraper stopped", level="warn", stage="idle"
        )
        background_scrape_store.update_progress(user_id, 0, "idle", "Stopped")


def ensure_background_scraper(user_id: int) -> None:
    background_scrape_store.touch_heartbeat(user_id)

    def factory(stop_event: threading.Event) -> threading.Thread:
        return threading.Thread(
            target=_background_loop,
            args=(user_id, stop_event),
            daemon=True,
            name=f"background-scrape-{user_id}",
        )

    background_scrape_store.start_worker_if_dead(user_id, factory)


def stop_background_scraper(user_id: int) -> None:
    background_scrape_store.stop_worker(user_id)
