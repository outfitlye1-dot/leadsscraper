import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from app.scraper.metrics import ScrapeMetrics

JobStatus = Literal["pending", "running", "paused", "completed", "failed", "cancelled"]
JobMode = Literal["single", "auto"]


@dataclass
class ScraperJobState:
    job_id: str
    user_id: int
    status: JobStatus = "pending"
    mode: JobMode = "single"
    progress: int = 0
    stage: str = "pending"
    message: str = "Waiting to start..."
    result: dict[str, Any] | None = None
    error: str | None = None
    cancel_requested: bool = False
    pause_requested: bool = False
    iteration: int = 0
    auto_kept_total: int = 0
    auto_deleted_total: int = 0
    auto_scraped_total: int = 0
    logs: list[dict[str, Any]] = field(default_factory=list)
    log_seq: int = 0
    checkpoint: dict[str, Any] | None = None
    failed_urls: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


MAX_JOB_LOGS = 250


class ScraperJobStore:
    def __init__(self):
        self._jobs: dict[str, ScraperJobState] = {}
        self._active_auto: dict[int, str] = {}
        self._metrics: dict[str, ScrapeMetrics] = {}
        self._lock = threading.Lock()

    def bind_metrics(self, job_id: str, metrics: ScrapeMetrics) -> None:
        with self._lock:
            self._metrics[job_id] = metrics

    def get_metrics(self, job_id: str) -> ScrapeMetrics | None:
        with self._lock:
            return self._metrics.get(job_id)

    def create(self, user_id: int, *, mode: JobMode = "single") -> str:
        job_id = str(uuid4())
        with self._lock:
            self._jobs[job_id] = ScraperJobState(job_id=job_id, user_id=user_id, mode=mode)
            if mode == "auto":
                self._active_auto[user_id] = job_id
        return job_id

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        stage: str | None = None,
        message: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = max(0, min(100, progress))
            if stage is not None:
                job.stage = stage
            if message is not None:
                job.message = message
            job.updated_at = datetime.now(UTC)

    def save_checkpoint(self, job_id: str, checkpoint: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.checkpoint = checkpoint
            job.updated_at = datetime.now(UTC)

    def add_failed_url(self, job_id: str, url: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if url not in job.failed_urls and len(job.failed_urls) < 200:
                job.failed_urls.append(url)

    def append_log(
        self,
        job_id: str,
        text: str,
        *,
        level: str = "info",
        stage: str = "",
    ) -> None:
        text = (text or "").strip()
        if not text:
            return
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if job.logs and job.logs[-1].get("text") == text:
                return
            job.log_seq += 1
            job.logs.append(
                {
                    "seq": job.log_seq,
                    "ts": datetime.now(UTC).isoformat(),
                    "level": level,
                    "stage": stage or job.stage,
                    "text": text,
                }
            )
            if len(job.logs) > MAX_JOB_LOGS:
                job.logs = job.logs[-MAX_JOB_LOGS:]
            job.updated_at = datetime.now(UTC)

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "completed"
            job.progress = 100
            job.stage = "done"
            job.message = result.get("message", "Scraping completed")
            job.result = result
            job.updated_at = datetime.now(UTC)
            self._clear_active_auto(job)
            self._metrics.pop(job_id, None)

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.stage = "error"
            job.message = error
            job.error = error
            job.updated_at = datetime.now(UTC)
            self._clear_active_auto(job)
            self._metrics.pop(job_id, None)

    def cancel(self, job_id: str, user_id: int) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.user_id != user_id:
                return False
            if job.status not in ("pending", "running", "paused"):
                return False
            job.cancel_requested = True
            job.status = "cancelled"
            job.message = "Job cancelled"
            job.updated_at = datetime.now(UTC)
            self._clear_active_auto(job)
            return True

    def request_cancel(self, job_id: str, user_id: int) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.user_id != user_id:
                return False
            if job.mode == "auto":
                if job.status not in ("pending", "running"):
                    return False
                job.cancel_requested = True
                job.message = "Stopping after current scrape round..."
                job.updated_at = datetime.now(UTC)
                return True
            if job.status not in ("pending", "running", "paused"):
                return False
            job.cancel_requested = True
            job.message = "Cancelling scrape..."
            job.updated_at = datetime.now(UTC)
            return True

    def request_pause(self, job_id: str, user_id: int) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.user_id != user_id or job.mode != "single":
                return False
            if job.status != "running":
                return False
            job.pause_requested = True
            job.status = "paused"
            job.message = "Paused"
            job.updated_at = datetime.now(UTC)
            return True

    def resume(self, job_id: str, user_id: int) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.user_id != user_id:
                return False
            if job.status != "paused":
                return False
            job.pause_requested = False
            job.status = "running"
            job.message = "Resumed"
            job.updated_at = datetime.now(UTC)
            return True

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job.cancel_requested)

    def is_paused(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job.pause_requested)

    def should_abort(self, job_id: str) -> bool:
        return self.is_cancelled(job_id) or self.is_paused(job_id)

    def set_iteration(self, job_id: str, iteration: int) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.iteration = iteration
            job.updated_at = datetime.now(UTC)

    def add_auto_stats(self, job_id: str, *, scraped: int, kept: int, deleted: int) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.auto_scraped_total += scraped
            job.auto_kept_total += kept
            job.auto_deleted_total += deleted
            job.updated_at = datetime.now(UTC)

    def get_active_auto_job(self, user_id: int) -> ScraperJobState | None:
        with self._lock:
            job_id = self._active_auto.get(user_id)
            if not job_id:
                return None
            job = self._jobs.get(job_id)
            if not job or job.mode != "auto" or job.status not in ("pending", "running"):
                return None
            return job

    def get_active_scrape_job(self, user_id: int) -> ScraperJobState | None:
        with self._lock:
            for job in self._jobs.values():
                if (
                    job.user_id == user_id
                    and job.mode == "single"
                    and job.status in ("pending", "running", "paused")
                ):
                    return job
            job_id = self._active_auto.get(user_id)
            if not job_id:
                return None
            job = self._jobs.get(job_id)
            if not job or job.mode != "auto" or job.status not in ("pending", "running"):
                return None
            return job

    def has_active_manual_job(self, user_id: int) -> bool:
        with self._lock:
            for job in self._jobs.values():
                if (
                    job.user_id == user_id
                    and job.mode == "single"
                    and job.status in ("pending", "running", "paused")
                ):
                    return True
            return False

    def has_active_scrape_job(self, user_id: int) -> bool:
        return self.has_active_manual_job(user_id) or self.get_active_auto_job(user_id) is not None

    def list_history(self, user_id: int, limit: int = 20) -> list[ScraperJobState]:
        with self._lock:
            jobs = [j for j in self._jobs.values() if j.user_id == user_id]
            jobs.sort(key=lambda j: j.updated_at, reverse=True)
            return jobs[:limit]

    def _clear_active_auto(self, job: ScraperJobState) -> None:
        if self._active_auto.get(job.user_id) == job.job_id:
            del self._active_auto[job.user_id]

    def get(self, job_id: str, user_id: int) -> ScraperJobState | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.user_id != user_id:
                return None
            return job

    def list_all(self, limit: int = 100) -> list[ScraperJobState]:
        with self._lock:
            jobs = list(self._jobs.values())
            jobs.sort(key=lambda j: j.updated_at, reverse=True)
            return jobs[:limit]

    def admin_cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.status not in ("pending", "running", "paused"):
                return False
            job.cancel_requested = True
            job.status = "cancelled"
            job.message = "Cancelled by admin"
            job.updated_at = datetime.now(UTC)
            self._clear_active_auto(job)
            return True


scraper_job_store = ScraperJobStore()