"""DB queue for WhatsApp Web inbound jobs."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.whatsapp_web import WhatsAppWebInboundJob
from app.services.whatsapp_web.dedupe import make_dedupe_key

logger = logging.getLogger(__name__)


class WhatsAppWebQueue:
    def __init__(self, db: Session) -> None:
        self.db = db

    def enqueue(
        self,
        *,
        chat_title: str,
        body: str,
        phone_hint: str | None = None,
    ) -> WhatsAppWebInboundJob | None:
        text = (body or "").strip()
        if not text:
            return None
        key = make_dedupe_key(chat_title=chat_title, body=text, phone_hint=phone_hint)
        existing = (
            self.db.query(WhatsAppWebInboundJob)
            .filter(WhatsAppWebInboundJob.dedupe_key == key)
            .first()
        )
        if existing:
            logger.debug("WA Web dedupe hit key=%s", key[:12])
            return None
        job = WhatsAppWebInboundJob(
            dedupe_key=key,
            chat_title=(chat_title or "").strip()[:255],
            phone_hint=(phone_hint or None),
            body=text[:8000],
            status="pending",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        logger.info("WA Web queued inbound id=%s title=%r", job.id, job.chat_title[:40])
        return job

    def claim_next(self) -> WhatsAppWebInboundJob | None:
        job = (
            self.db.query(WhatsAppWebInboundJob)
            .filter(WhatsAppWebInboundJob.status == "pending")
            .order_by(WhatsAppWebInboundJob.id.asc())
            .first()
        )
        if not job:
            return None
        job.status = "processing"
        job.attempts = int(job.attempts or 0) + 1
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_done(
        self,
        job: WhatsAppWebInboundJob,
        *,
        reply_body: str | None = None,
        lead_id: int | None = None,
        user_id: int | None = None,
        ai_replied: bool = False,
    ) -> None:
        job.status = "done"
        job.reply_body = reply_body
        job.lead_id = lead_id
        job.user_id = user_id
        job.ai_replied = ai_replied
        job.processed_at = datetime.now(UTC)
        job.error_message = None
        self.db.commit()

    def mark_skipped(self, job: WhatsAppWebInboundJob, reason: str) -> None:
        job.status = "skipped"
        job.error_message = (reason or "")[:2000]
        job.processed_at = datetime.now(UTC)
        self.db.commit()

    def mark_failed(self, job: WhatsAppWebInboundJob, error: str) -> None:
        job.status = "failed"
        job.error_message = (error or "")[:2000]
        job.processed_at = datetime.now(UTC)
        self.db.commit()

    def recent(self, limit: int = 20) -> list[WhatsAppWebInboundJob]:
        return (
            self.db.query(WhatsAppWebInboundJob)
            .order_by(WhatsAppWebInboundJob.id.desc())
            .limit(max(1, min(limit, 100)))
            .all()
        )

    def chat_history_text(
        self,
        *,
        chat_title: str,
        phone_hint: str | None = None,
        exclude_job_id: int | None = None,
        limit: int = 8,
    ) -> str:
        """Build short Customer/You history for unknown-number AI replies."""
        import re

        title = (chat_title or "").strip()
        digits = re.sub(r"\D", "", phone_hint or "")
        rows = (
            self.db.query(WhatsAppWebInboundJob)
            .filter(
                WhatsAppWebInboundJob.status == "done",
                WhatsAppWebInboundJob.ai_replied.is_(True),
            )
            .order_by(WhatsAppWebInboundJob.id.desc())
            .limit(60)
            .all()
        )
        matched: list[WhatsAppWebInboundJob] = []
        for r in rows:
            if exclude_job_id and int(r.id) == int(exclude_job_id):
                continue
            same_title = bool(title) and (r.chat_title or "").strip().lower() == title.lower()
            r_digits = re.sub(r"\D", "", r.phone_hint or "")
            same_phone = (
                len(digits) >= 10
                and len(r_digits) >= 10
                and (digits[-10:] == r_digits[-10:])
            )
            if same_title or same_phone:
                matched.append(r)
            if len(matched) >= limit:
                break

        lines: list[str] = []
        for idx, r in enumerate(reversed(matched), start=1):
            if r.body:
                lines.append(f"{idx}. Customer: {(r.body or '').strip()[:240]}")
            if r.reply_body:
                lines.append(f"{idx}. You (already sent): {(r.reply_body or '').strip()[:240]}")
        return "\n".join(lines)
