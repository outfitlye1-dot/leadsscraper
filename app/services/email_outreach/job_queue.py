"""Persistent outreach job queue backed by the database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.email_outreach import OutreachJob, OutreachJobStatus, OutreachJobType
from app.utils.datetime_utils import as_utc


class OutreachJobQueue:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(
        self,
        user_id: int,
        job_type: OutreachJobType,
        payload: dict | None = None,
        *,
        scheduled_at: datetime | None = None,
        priority: int = 0,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
    ) -> OutreachJob:
        if idempotency_key:
            existing = (
                self.db.query(OutreachJob)
                .filter(OutreachJob.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                if existing.status in (
                    OutreachJobStatus.pending,
                    OutreachJobStatus.running,
                ):
                    return existing
                idempotency_key = f"{idempotency_key}_{int(datetime.now(UTC).timestamp() * 1000)}"

        job = OutreachJob(
            user_id=user_id,
            job_type=job_type,
            payload=payload or {},
            status=OutreachJobStatus.pending,
            priority=priority,
            max_attempts=max_attempts,
            idempotency_key=idempotency_key,
            scheduled_at=scheduled_at or datetime.now(UTC),
        )
        self.db.add(job)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            if idempotency_key:
                existing = (
                    self.db.query(OutreachJob)
                    .filter(OutreachJob.idempotency_key == idempotency_key)
                    .first()
                )
                if existing:
                    return existing
            raise
        self.db.refresh(job)
        return job

    def claim_next(self) -> OutreachJob | None:
        now = datetime.now(UTC)
        candidates = (
            self.db.query(OutreachJob)
            .filter(OutreachJob.status == OutreachJobStatus.pending)
            .order_by(OutreachJob.priority.desc(), OutreachJob.scheduled_at.asc())
            .limit(50)
            .all()
        )
        job = next(
            (row for row in candidates if as_utc(row.scheduled_at) <= now),
            None,
        )
        if not job:
            return None

        job.status = OutreachJobStatus.running
        job.started_at = now
        job.attempts += 1
        self.db.commit()
        self.db.refresh(job)
        return job

    def complete(self, job: OutreachJob) -> None:
        job.status = OutreachJobStatus.completed
        job.completed_at = datetime.now(UTC)
        job.error_message = None
        job.idempotency_key = None
        self.db.commit()

    def fail(self, job: OutreachJob, error: str) -> None:
        if job.attempts < job.max_attempts:
            job.status = OutreachJobStatus.pending
            job.scheduled_at = datetime.now(UTC) + timedelta(minutes=2 ** job.attempts)
            job.error_message = error
        else:
            job.status = OutreachJobStatus.failed
            job.completed_at = datetime.now(UTC)
            job.error_message = error
            job.idempotency_key = None
        self.db.commit()

    def recover_stale_running(self, stale_minutes: int = 15) -> int:
        cutoff = datetime.now(UTC) - timedelta(minutes=stale_minutes)
        running = (
            self.db.query(OutreachJob)
            .filter(OutreachJob.status == OutreachJobStatus.running)
            .all()
        )
        recovered = 0
        for job in running:
            if job.started_at is None or as_utc(job.started_at) < cutoff:
                job.status = OutreachJobStatus.pending
                job.started_at = None
                recovered += 1
        if recovered:
            self.db.commit()
        return recovered

    def list_pending_for_user(self, user_id: int, limit: int = 50) -> list[OutreachJob]:
        return (
            self.db.query(OutreachJob)
            .filter(
                OutreachJob.user_id == user_id,
                OutreachJob.status.in_(
                    [OutreachJobStatus.pending, OutreachJobStatus.running]
                ),
            )
            .order_by(OutreachJob.scheduled_at.asc())
            .limit(limit)
            .all()
        )
