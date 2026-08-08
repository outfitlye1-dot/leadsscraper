from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import logging

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.common import (
    AutoScrapeStartRequest,
    AutoScrapeStopResponse,
    BackgroundScrapeStatusResponse,
    DailyScrapeStartResponse,
    DailyScrapeStatusResponse,
    DemoScrapeRequest,
    DemoScrapeResponse,
    ScrapeMetricsResponse,
    ScraperAgentStatus,
    ScraperJobControlResponse,
    ScraperJobHistoryResponse,
    ScraperJobStartResponse,
    ScraperJobStatusResponse,
    ScraperStartRequest,
    ScraperStartResponse,
)
from app.scraper.api.dashboard import build_scrape_dashboard
from app.services.daily_scrape_service import DailyScrapeService
from app.services.demo_scrape_service import DemoScrapeService
from app.services.background_scrape_runner import (
    ensure_background_scraper,
    stop_background_scraper,
)
from app.services.background_scrape_store import background_scrape_store
from app.services.scraper_job_store import scraper_job_store
from app.services.scraper_runner import (
    start_auto_scraper_job,
    start_scraper_job,
    stop_auto_scraper_job,
)
from app.utils.demo_rate_limit import allow_demo_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scraper", tags=["scraper"])


@router.post(
    "/demo",
    response_model=DemoScrapeResponse,
    summary="Public demo — extract 4 leads without login",
    description="Landing page preview. Rate-limited by IP. Does not save leads to database.",
)
def demo_scrape(data: DemoScrapeRequest, request: Request) -> DemoScrapeResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not allow_demo_request(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demo limit reached. Create a free account for unlimited scraping.",
        )
    try:
        return DemoScrapeService().run(data.keyword, data.location)
    except Exception as exc:
        logger.exception("Demo scrape route failed: %s", exc)
        return DemoScrapeResponse(
            success=False,
            count=0,
            total_estimated=0,
            message="Demo scrape failed. Please try again in a moment.",
            leads=[],
        )


@router.get(
    "/daily/status",
    response_model=DailyScrapeStatusResponse,
    summary="Daily one-click scrape status",
    responses={401: {"description": "Not authenticated"}},
)
def get_daily_scrape_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyScrapeStatusResponse:
    return DailyScrapeService(db).get_status(current_user)


@router.post(
    "/daily/start",
    response_model=DailyScrapeStartResponse,
    summary="Start daily 100 leads scrape (once per day)",
    responses={
        400: {"description": "Profile or query missing"},
        401: {"description": "Not authenticated"},
        429: {"description": "Already ran today"},
    },
)
def start_daily_scrape(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyScrapeStartResponse:
    return DailyScrapeService(db).start(current_user)


@router.post(
    "/start",
    response_model=ScraperJobStartResponse,
    summary="Start all-in-one lead scraper (background job)",
    description=(
        "Starts scraping in the background and returns a job_id. "
        "Poll GET /api/scraper/jobs/{job_id} for progress and final result."
    ),
    responses={
        401: {"description": "Not authenticated"},
        409: {"description": "Auto or manual scrape already running"},
    },
)
def start_scraper(
    data: ScraperStartRequest,
    current_user: User = Depends(get_current_user),
) -> ScraperJobStartResponse:
    job_id = start_scraper_job(current_user.id, data)
    return ScraperJobStartResponse(job_id=job_id)


@router.post(
    "/auto/start",
    response_model=ScraperJobStartResponse,
    summary="Start continuous auto scraping (phone leads only)",
    description=(
        "Runs Internet scrape rounds in a loop until stopped. Each round uses a rotated "
        "search query. After each round, leads without a phone number are deleted automatically. "
        "Phone leads stay in your inbox for manual review."
    ),
    responses={
        401: {"description": "Not authenticated"},
        409: {"description": "Auto scrape already running"},
    },
)
def start_auto_scraper(
    data: AutoScrapeStartRequest,
    current_user: User = Depends(get_current_user),
) -> ScraperJobStartResponse:
    job_id = start_auto_scraper_job(
        current_user.id,
        data,
        interval_seconds=data.interval_seconds,
        country=data.country,
        parallel_agents=data.parallel_agents,
    )
    return ScraperJobStartResponse(job_id=job_id)


@router.post(
    "/auto/stop",
    response_model=AutoScrapeStopResponse,
    summary="Stop continuous auto scraping",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "No auto scrape running"},
    },
)
def stop_auto_scraper(
    current_user: User = Depends(get_current_user),
) -> AutoScrapeStopResponse:
    stopped = stop_auto_scraper_job(current_user.id)
    return AutoScrapeStopResponse(
        success=True,
        message="Stopped" if stopped else "Already stopped",
    )


@router.get(
    "/active",
    response_model=ScraperJobStatusResponse | None,
    summary="Get active manual or auto scrape job",
    responses={401: {"description": "Not authenticated"}},
)
def get_active_scraper_job(
    current_user: User = Depends(get_current_user),
) -> ScraperJobStatusResponse | None:
    job = scraper_job_store.get_active_scrape_job(current_user.id)
    if not job:
        return None
    return _job_to_response(job)


@router.get(
    "/auto/status",
    response_model=ScraperJobStatusResponse | None,
    summary="Get active auto scrape job status",
    responses={401: {"description": "Not authenticated"}},
)
def get_auto_scraper_status(
    current_user: User = Depends(get_current_user),
) -> ScraperJobStatusResponse | None:
    job = scraper_job_store.get_active_auto_job(current_user.id)
    if not job:
        return None
    return _job_to_response(job)


@router.post(
    "/background/heartbeat",
    response_model=BackgroundScrapeStatusResponse,
    summary="Session keepalive for background scraper (does not auto-start)",
)
def background_scraper_heartbeat(
    current_user: User = Depends(get_current_user),
) -> BackgroundScrapeStatusResponse:
    try:
        # Keepalive only — never start scrapes for every logged-in account
        ensure_background_scraper(current_user.id, start_if_stopped=False)
        return BackgroundScrapeStatusResponse(**background_scrape_store.get_status(current_user.id))
    except Exception as exc:
        logger.warning("Background heartbeat soft-fail for user %s: %s", current_user.id, exc)
        return BackgroundScrapeStatusResponse(
            active=True,
            running=False,
            message="Heartbeat deferred",
        )


@router.post(
    "/background/stop",
    response_model=AutoScrapeStopResponse,
    summary="Stop silent background scraper",
)
def stop_background_scraper_route(
    current_user: User = Depends(get_current_user),
) -> AutoScrapeStopResponse:
    try:
        stop_background_scraper(current_user.id)
    except Exception as exc:
        logger.warning("Background stop soft-fail for user %s: %s", current_user.id, exc)
    return AutoScrapeStopResponse(success=True, message="Background scraper stopped.")


@router.get(
    "/background/status",
    response_model=BackgroundScrapeStatusResponse,
    summary="Background scraper status",
)
def get_background_scraper_status(
    current_user: User = Depends(get_current_user),
) -> BackgroundScrapeStatusResponse:
    try:
        # Read-only — do not start/restart the worker on every status poll
        return BackgroundScrapeStatusResponse(**background_scrape_store.get_status(current_user.id))
    except Exception as exc:
        logger.warning("Background status soft-fail for user %s: %s", current_user.id, exc)
        return BackgroundScrapeStatusResponse(
            active=False,
            running=False,
            message="Unavailable",
        )


def _job_to_response(job) -> ScraperJobStatusResponse:
    result = None
    if job.result:
        result = ScraperStartResponse(**job.result)
    live_metrics = None
    metrics = scraper_job_store.get_metrics(job.job_id)
    if metrics:
        live_metrics = ScrapeMetricsResponse(**build_scrape_dashboard(metrics))
    raw_agents = list(getattr(job, "agents", None) or [])
    agents = []
    for raw in raw_agents:
        try:
            agents.append(ScraperAgentStatus(**raw))
        except Exception:
            continue
    return ScraperJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        mode=job.mode,
        progress=job.progress,
        stage=job.stage,
        message=job.message,
        result=result,
        error=job.error,
        iteration=job.iteration,
        auto_kept_total=job.auto_kept_total,
        auto_deleted_total=job.auto_deleted_total,
        auto_scraped_total=job.auto_scraped_total,
        cancel_requested=job.cancel_requested,
        pause_requested=getattr(job, "pause_requested", False),
        live_metrics=live_metrics,
        failed_urls=list(getattr(job, "failed_urls", []) or [])[:50],
        logs=job.logs,
        agents=agents,
    )


@router.post(
    "/jobs/{job_id}/pause",
    response_model=ScraperJobControlResponse,
    summary="Pause a running manual scrape job",
)
def pause_scraper_job(job_id: str, current_user: User = Depends(get_current_user)):
    if not scraper_job_store.request_pause(job_id, current_user.id):
        raise HTTPException(status_code=404, detail="Job not found or cannot be paused")
    return ScraperJobControlResponse(success=True, message="Job paused", job_id=job_id)


@router.post(
    "/jobs/{job_id}/resume",
    response_model=ScraperJobControlResponse,
    summary="Resume a paused manual scrape job",
)
def resume_scraper_job(job_id: str, current_user: User = Depends(get_current_user)):
    if not scraper_job_store.resume(job_id, current_user.id):
        raise HTTPException(status_code=404, detail="Job not found or not paused")
    return ScraperJobControlResponse(success=True, message="Job resumed", job_id=job_id)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=ScraperJobControlResponse,
    summary="Cancel a scrape job",
)
def cancel_scraper_job(job_id: str, current_user: User = Depends(get_current_user)):
    # Idempotent: stale/localStorage job ids after restart should not break Stop
    if not scraper_job_store.request_cancel(job_id, current_user.id):
        return ScraperJobControlResponse(
            success=True,
            message="Already stopped",
            job_id=job_id,
        )
    return ScraperJobControlResponse(success=True, message="Stopped", job_id=job_id)


@router.get(
    "/jobs/{job_id}/metrics",
    response_model=ScrapeMetricsResponse,
    summary="Live scrape metrics for a job",
)
def get_job_metrics(job_id: str, current_user: User = Depends(get_current_user)):
    job = scraper_job_store.get(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    metrics = scraper_job_store.get_metrics(job_id)
    if not metrics and job.result and job.result.get("scrape_metrics"):
        return ScrapeMetricsResponse(**job.result["scrape_metrics"])
    if not metrics:
        return ScrapeMetricsResponse()
    return ScrapeMetricsResponse(**build_scrape_dashboard(metrics))


@router.get(
    "/jobs/{job_id}/failed-urls",
    summary="Failed URLs for a scrape job",
)
def get_job_failed_urls(job_id: str, current_user: User = Depends(get_current_user)):
    job = scraper_job_store.get(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "failed_urls": list(job.failed_urls)}


@router.get(
    "/jobs/history",
    response_model=ScraperJobHistoryResponse,
    summary="Recent scrape job history",
)
def get_job_history(current_user: User = Depends(get_current_user)):
    jobs = scraper_job_store.list_history(current_user.id)
    return ScraperJobHistoryResponse(jobs=[_job_to_response(j) for j in jobs])


@router.get(
    "/jobs/{job_id}",
    response_model=ScraperJobStatusResponse,
    summary="Get scraper job progress",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Job not found"},
    },
)
def get_scraper_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> ScraperJobStatusResponse:
    job = scraper_job_store.get(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_response(job)
