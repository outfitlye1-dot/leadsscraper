"""Background worker for email outreach jobs — survives restarts via DB queue."""

from __future__ import annotations

import logging
import threading
import time

from app.core.config import get_settings
from app.database.database import SessionLocal
from app.models.email_outreach import OutreachJobType
from app.services.email_outreach.agent import AiOutreachAgent
from app.services.email_outreach.campaign import EmailOutreachCampaignService
from app.services.email_outreach.job_queue import OutreachJobQueue
from app.services.email_outreach.send import EmailSendService
from app.services.email_outreach.sync import InboxSyncService

logger = logging.getLogger(__name__)


class OutreachWorker:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_sync: dict[int, float] = {}

    def start(self) -> None:
        settings = get_settings()
        if not settings.OUTREACH_WORKER_ENABLED:
            logger.info("Outreach worker disabled")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="outreach-worker")
        self._thread.start()
        logger.info("Outreach worker started")

    def stop(self) -> None:
        self._stop.set()

    def _run_loop(self) -> None:
        settings = get_settings()
        idle_poll = max(settings.OUTREACH_WORKER_POLL_SECONDS, 15)
        while not self._stop.is_set():
            settings = get_settings()
            if not settings.OUTREACH_WORKER_ENABLED:
                time.sleep(idle_poll)
                continue

            db = SessionLocal()
            had_work = False
            try:
                queue = OutreachJobQueue(db)
                queue.recover_stale_running()
                job = queue.claim_next()
                if job:
                    had_work = True
                    job_id = job.id
                    job_type = job.job_type
                    user_id = job.user_id
                    payload = dict(job.payload or {})
                    db.close()
                    db = None
                    self._process_job(job_id, job_type, user_id, payload)
                else:
                    self._maybe_schedule_syncs(db)
                    self._maybe_schedule_agent_cycles(db)
            except Exception:
                logger.exception("Outreach worker loop error")
            finally:
                if db is not None:
                    db.close()
            time.sleep(2 if had_work else idle_poll)

    def _maybe_schedule_syncs(self, db) -> None:
        settings = get_settings()
        from app.models.email_outreach import EmailAccount, EmailAccountStatus, OutreachJob, OutreachJobStatus, OutreachJobType as JT

        accounts = db.query(EmailAccount).filter(EmailAccount.status == EmailAccountStatus.connected).all()
        now = time.time()
        for account in accounts:
            last = self._last_sync.get(account.id, 0)
            if now - last < settings.OUTREACH_SYNC_INTERVAL_SECONDS:
                continue
            existing = (
                db.query(OutreachJob)
                .filter(
                    OutreachJob.user_id == account.user_id,
                    OutreachJob.job_type == JT.sync_inbox,
                    OutreachJob.status.in_([OutreachJobStatus.pending, OutreachJobStatus.running]),
                )
                .first()
            )
            if not existing:
                OutreachJobQueue(db).enqueue(
                    account.user_id,
                    OutreachJobType.sync_inbox,
                    {"account_id": account.id},
                    idempotency_key=f"sync_{account.id}_{int(now // settings.OUTREACH_SYNC_INTERVAL_SECONDS)}",
                )
            self._last_sync[account.id] = now

    def _maybe_schedule_agent_cycles(self, db) -> None:
        from app.models.email_outreach import EmailOutreachSettings, OutreachJob, OutreachJobStatus

        settings_rows = (
            db.query(EmailOutreachSettings)
            .filter(
                EmailOutreachSettings.agent_running.is_(True),
                EmailOutreachSettings.agent_paused.is_(False),
            )
            .all()
        )
        for settings in settings_rows:
            existing = (
                db.query(OutreachJob)
                .filter(
                    OutreachJob.user_id == settings.user_id,
                    OutreachJob.job_type == OutreachJobType.agent_cycle,
                    OutreachJob.status.in_([OutreachJobStatus.pending, OutreachJobStatus.running]),
                )
                .first()
            )
            if not existing:
                OutreachJobQueue(db).enqueue(
                    settings.user_id,
                    OutreachJobType.agent_cycle,
                    {"campaign_id": settings.standing_campaign_id},
                    idempotency_key=f"agent_cycle_{settings.user_id}_{int(time.time() // 120)}",
                    priority=10,
                )

    def _process_job(self, job_id: int, job_type, user_id: int, payload: dict) -> None:
        from app.models.email_outreach import OutreachJob

        db = SessionLocal()
        queue = OutreachJobQueue(db)
        job = db.query(OutreachJob).filter(OutreachJob.id == job_id).first()
        if not job:
            db.close()
            return
        try:
            if job_type == OutreachJobType.send_email:
                if payload.get("reply_draft_id"):
                    self._send_reply_draft(db, user_id, payload)
                else:
                    EmailSendService(db).send_outreach_email(
                        user_id,
                        payload["outreach_email_id"],
                        pilot=bool(payload.get("pilot")),
                    )
            elif job_type == OutreachJobType.process_campaign:
                EmailOutreachCampaignService(db).process_campaign(
                    user_id, payload["campaign_id"]
                )
            elif job_type == OutreachJobType.sync_inbox:
                InboxSyncService(db).sync_account(user_id, payload["account_id"])
            elif job_type == OutreachJobType.schedule_followups:
                EmailOutreachCampaignService(db).schedule_follow_ups(
                    user_id, payload["campaign_id"]
                )
            elif job_type == OutreachJobType.agent_cycle:
                AiOutreachAgent(db).run_agent_cycle(user_id)
            elif job_type == OutreachJobType.process_lead:
                agent = AiOutreachAgent(db)
                settings = agent.repo.get_or_create_settings(user_id)
                campaign_id = payload.get("campaign_id") or settings.standing_campaign_id
                if not campaign_id:
                    campaign = agent.get_or_create_standing_campaign(user_id)
                    campaign_id = campaign.id
                lead = agent.lead_repo.get_by_id(user_id, payload["lead_id"])
                if lead:
                    agent.process_single_lead(user_id, lead, campaign_id)
            elif job_type in (
                OutreachJobType.verify_emails,
                OutreachJobType.generate_emails,
            ):
                EmailOutreachCampaignService(db).process_campaign(
                    user_id, payload["campaign_id"]
                )
            job = db.query(OutreachJob).filter(OutreachJob.id == job_id).first()
            if job:
                queue.complete(job)
        except Exception as exc:
            logger.warning("Job %s failed: %s", job_id, exc)
            job = db.query(OutreachJob).filter(OutreachJob.id == job_id).first()
            if job:
                queue.fail(job, str(exc))
        finally:
            db.close()

    def _send_reply_draft(self, db, user_id: int, payload: dict) -> None:
        from app.models.email_outreach import AiReplyDraftStatus, ConversationMessage
        from app.models.lead import Lead
        from app.repositories.email_outreach_repository import EmailOutreachRepository
        from app.services.email_outreach.transport import send_email

        repo = EmailOutreachRepository(db)
        draft = repo.get_ai_draft(user_id, payload["reply_draft_id"])
        if not draft:
            return
        conversation = repo.get_conversation(user_id, draft.conversation_id)
        if not conversation:
            return
        account = (
            repo.get_account(user_id, conversation.email_account_id)
            if conversation.email_account_id
            else repo.get_default_account(user_id)
        )
        if not account:
            raise ValueError("No email account")

        lead = db.query(Lead).filter(Lead.id == conversation.lead_id).first()
        to_email = lead.email if lead else ""
        if not to_email:
            return

        message_id = send_email(account, to_email, draft.draft_subject, draft.draft_body)
        msg = ConversationMessage(
            conversation_id=conversation.id,
            direction="outbound",
            from_email=account.email_address,
            to_email=to_email,
            subject=draft.draft_subject,
            body_text=draft.draft_body,
            external_message_id=message_id,
        )
        db.add(msg)
        draft.status = AiReplyDraftStatus.sent
        db.commit()


outreach_worker = OutreachWorker()
