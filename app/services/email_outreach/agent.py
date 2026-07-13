"""AI Outreach Agent — autonomous SDR that processes saved leads."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.email_outreach import (
    AgentActivityLog,
    EmailAccountStatus,
    EmailTimelineEventType,
    NotificationType,
    OutreachCampaignStatus,
    OutreachEmailStatus,
    OutreachJobType,
)
from app.models.lead import Lead, LeadStatus
from app.models.user import User
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.repositories.lead_repository import LeadRepository
from app.services.email_outreach.generation import EmailGenerationService
from app.services.email_outreach.job_queue import OutreachJobQueue
from app.utils.datetime_utils import as_utc
from app.services.email_outreach.notifications import NotificationService
from app.services.email_outreach.verification import can_send_to_email, verify_outreach_email

STANDING_CAMPAIGN_NAME = "AI Agent — Auto Outreach"


class AiOutreachAgent:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)
        self.lead_repo = LeadRepository(db)
        self.queue = OutreachJobQueue(db)
        self.notifications = NotificationService(db)

    def _log(
        self,
        user_id: int,
        activity_type: str,
        message: str,
        *,
        lead_id: int | None = None,
        level: str = "info",
    ) -> None:
        self.db.add(
            AgentActivityLog(
                user_id=user_id,
                activity_type=activity_type,
                message=message,
                lead_id=lead_id,
                level=level,
            )
        )
        self.db.commit()

    def is_within_working_hours(self, settings) -> bool:
        now = datetime.now(UTC)
        if not settings.weekends_enabled and now.weekday() >= 5:
            return False
        hour = now.hour
        start = settings.working_hours_start
        end = settings.working_hours_end
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end

    def get_or_create_standing_campaign(self, user_id: int):
        settings = self.repo.get_or_create_settings(user_id)
        if settings.standing_campaign_id:
            campaign = self.repo.get_campaign(user_id, settings.standing_campaign_id)
            if campaign:
                return campaign

        account = self.repo.get_default_account(user_id)
        campaign = self.repo.create_campaign(
            user_id,
            {
                "name": STANDING_CAMPAIGN_NAME,
                "email_account_id": account.id if account else None,
                "status": OutreachCampaignStatus.active,
                "automation_enabled": True,
                "require_review": settings.require_review,
                "follow_up_enabled": settings.auto_follow_up,
                "lead_filter_saved_only": True,
                "started_at": datetime.now(UTC),
            },
        )
        from app.services.email_outreach.campaign import DEFAULT_FOLLOW_UP_STEPS

        self.repo.set_follow_up_steps(campaign.id, [dict(s) for s in DEFAULT_FOLLOW_UP_STEPS])
        settings.standing_campaign_id = campaign.id
        settings.automation_enabled = True
        self.db.commit()
        return campaign

    def start_agent(self, user: User) -> dict:
        settings = self.repo.get_or_create_settings(user.id)
        account = self.repo.get_default_account(user.id)
        if not account or account.status != EmailAccountStatus.connected:
            raise HTTPException(
                status_code=400,
                detail="Connect Gmail first before starting the AI Agent.",
            )

        campaign = self.get_or_create_standing_campaign(user.id)
        settings.agent_running = True
        settings.agent_paused = False
        settings.automation_enabled = True
        settings.last_agent_run_at = datetime.now(UTC)
        delay_min = max(settings.agent_batch_delay_minutes, 1)
        batch_at = datetime.now(UTC) + timedelta(minutes=delay_min)
        self.db.commit()

        self._log(
            user.id,
            "agent_started",
            f"AI Agent started — daily batch in {delay_min} min (today's leads, up to daily limit)",
        )
        self.notifications.notify(
            user.id,
            NotificationType.agent_started,
            "AI Agent Started",
            f"Outreach batch scheduled in {delay_min} minutes for today's leads.",
        )
        self.queue.enqueue(
            user.id,
            OutreachJobType.agent_cycle,
            {"campaign_id": campaign.id, "daily_batch": True},
            scheduled_at=batch_at,
            idempotency_key=f"agent_daily_batch_{user.id}_{int(batch_at.timestamp())}",
            priority=20,
        )

        pilot_info = self._run_pilot_email(user.id, campaign.id)

        msg = f"AI Agent started — pilot email to {pilot_info['to_email']}" if pilot_info else (
            f"AI Agent started — no leads with email yet; batch in {delay_min} min"
        )
        if pilot_info and delay_min > 0:
            msg += f"; remaining leads in {delay_min} min"

        return {
            "status": "running",
            "campaign_id": campaign.id,
            "message": msg,
            "batch_scheduled_at": batch_at.isoformat(),
            "pilot_email": pilot_info,
        }

    def stop_agent(self, user: User) -> dict:
        settings = self.repo.get_or_create_settings(user.id)
        settings.agent_running = False
        settings.agent_paused = False
        self.db.commit()
        self._log(user.id, "agent_stopped", "AI Outreach Agent stopped")
        self.notifications.notify(
            user.id,
            NotificationType.agent_stopped,
            "AI Agent Stopped",
            "Outreach automation has been paused.",
        )
        return {"status": "stopped", "message": "AI Agent stopped"}

    def pause_agent(self, user: User) -> dict:
        settings = self.repo.get_or_create_settings(user.id)
        settings.agent_paused = True
        self.db.commit()
        self._log(user.id, "agent_paused", "AI Outreach Agent paused")
        return {"status": "paused", "message": "AI Agent paused"}

    def resume_agent(self, user: User) -> dict:
        settings = self.repo.get_or_create_settings(user.id)
        if not settings.agent_running:
            return self.start_agent(user)
        settings.agent_paused = False
        self.db.commit()
        self._log(user.id, "agent_resumed", "AI Outreach Agent resumed")
        self.queue.enqueue(
            user.id,
            OutreachJobType.agent_cycle,
            {},
            priority=20,
        )
        return {"status": "running", "message": "AI Agent resumed"}

    def get_agent_status(self, user: User) -> dict:
        settings = self.repo.get_or_create_settings(user.id)
        account = self.repo.get_default_account(user.id)
        sent_today = self.repo.count_sent_today(user.id)
        return {
            "agent_running": settings.agent_running,
            "agent_paused": settings.agent_paused,
            "automation_enabled": settings.automation_enabled,
            "gmail_connected": bool(
                account and account.status == EmailAccountStatus.connected
            ),
            "gmail_email": account.email_address if account else None,
            "daily_limit": settings.daily_send_limit,
            "emails_sent_today": sent_today,
            "emails_remaining_today": max(0, settings.daily_send_limit - sent_today),
            "last_sync_at": account.last_sync_at.isoformat() if account and account.last_sync_at else None,
            "last_agent_run_at": (
                settings.last_agent_run_at.isoformat() if settings.last_agent_run_at else None
            ),
            "standing_campaign_id": settings.standing_campaign_id,
            "within_working_hours": self.is_within_working_hours(settings),
            "batch_delay_minutes": settings.agent_batch_delay_minutes,
        }

    def on_leads_saved(self, user_id: int, lead_ids: list[int]) -> None:
        settings = self.repo.get_or_create_settings(user_id)
        if not settings.agent_running or settings.agent_paused:
            return
        delay_min = max(settings.agent_batch_delay_minutes, 1)
        batch_at = datetime.now(UTC) + timedelta(minutes=delay_min)
        self.queue.enqueue(
            user_id,
            OutreachJobType.agent_cycle,
            {"daily_batch": True},
            scheduled_at=batch_at,
            idempotency_key=f"agent_batch_after_save_{user_id}_{int(batch_at.timestamp() // 60)}",
            priority=15,
        )

    def run_agent_cycle(self, user_id: int) -> dict:
        settings = self.repo.get_or_create_settings(user_id)
        if not settings.agent_running or settings.agent_paused:
            return {"skipped": True, "reason": "agent_not_running"}

        if not self.is_within_working_hours(settings):
            self._log(user_id, "outside_hours", "Agent idle — outside working hours", level="warn")
            return {"skipped": True, "reason": "outside_working_hours"}

        campaign = self.get_or_create_standing_campaign(user_id)
        settings.last_agent_run_at = datetime.now(UTC)
        self.db.commit()

        remaining_today = max(
            0, settings.daily_send_limit - self.repo.count_sent_today(user_id)
        )
        processed = 0
        new_leads = self._find_daily_batch_leads(user_id, campaign.id, remaining_today)
        if remaining_today == 0:
            self._log(
                user_id,
                "daily_limit",
                "Daily send limit reached — batch skipped until tomorrow",
                level="warn",
            )
        else:
            batch_leads = new_leads[:remaining_today]
            if batch_leads:
                self._log(
                    user_id,
                    "daily_batch",
                    f"Starting daily batch — {len(batch_leads)} lead(s) (limit: {remaining_today} remaining today)",
                )
            for lead in batch_leads:
                if not lead.is_saved:
                    lead.is_saved = True
                    lead.saved_at = datetime.now(UTC)
                    self.db.commit()
                if self.process_single_lead(user_id, lead, campaign.id):
                    processed += 1

        # Process due follow-ups
        due_followups = self._find_due_followups(user_id, campaign.id)
        for email in due_followups:
            self.queue.enqueue(
                user_id,
                OutreachJobType.send_email,
                {"outreach_email_id": email.id},
                idempotency_key=f"send_{email.id}",
            )

        # Schedule inbox sync
        account = self.repo.get_default_account(user_id)
        if account:
            self.queue.enqueue(
                user_id,
                OutreachJobType.sync_inbox,
                {"account_id": account.id},
                idempotency_key=f"sync_{account.id}_{int(datetime.now(UTC).timestamp() // 120)}",
            )

        self._log(
            user_id,
            "agent_cycle",
            f"Agent cycle complete — {processed} lead(s) emailed today, {len(due_followups)} follow-up(s) due",
        )

        # Re-schedule next cycle if still running
        if settings.agent_running and not settings.agent_paused:
            self.queue.enqueue(
                user_id,
                OutreachJobType.agent_cycle,
                {"campaign_id": campaign.id},
                scheduled_at=datetime.now(UTC) + timedelta(minutes=2),
                idempotency_key=f"agent_cycle_next_{user_id}_{int(datetime.now(UTC).timestamp())}",
                priority=5,
            )

        return {"processed": processed, "due_followups": len(due_followups)}

    def _today_start(self) -> datetime:
        return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    def _find_daily_batch_leads(
        self, user_id: int, campaign_id: int, limit: int
    ) -> list[Lead]:
        """Today's new leads first, then saved leads with email, up to daily remaining quota."""
        if limit <= 0:
            return []

        todays = self._find_todays_unprocessed_leads(user_id, campaign_id)
        if len(todays) >= limit:
            return todays[:limit]

        batch = list(todays)
        seen = {lead.id for lead in batch}
        for lead in self._find_unprocessed_saved_leads(user_id, campaign_id):
            if lead.id in seen:
                continue
            batch.append(lead)
            seen.add(lead.id)
            if len(batch) >= limit:
                break
        return batch

    def _find_todays_unprocessed_leads(self, user_id: int, campaign_id: int) -> list[Lead]:
        """Leads scraped/found today with email, not yet emailed."""
        today = self._today_start()
        existing_emails = self.repo.list_outreach_emails(user_id, campaign_id=campaign_id, limit=5000)
        processed_lead_ids = {e.lead_id for e in existing_emails if e.follow_up_step == 0}

        todays = (
            self.db.query(Lead)
            .filter(
                Lead.user_id == user_id,
                Lead.email.isnot(None),
                Lead.email != "",
            )
            .order_by(Lead.created_at.desc())
            .limit(500)
            .all()
        )
        return [
            l
            for l in todays
            if l.id not in processed_lead_ids
            and l.email
            and as_utc(l.created_at) >= today
        ]

    def _find_unprocessed_saved_leads(self, user_id: int, campaign_id: int) -> list[Lead]:
        all_saved = self.lead_repo.list_for_campaign_run(user_id, limit=500)
        saved_with_email = [l for l in all_saved if l.is_saved and l.email]
        existing_emails = self.repo.list_outreach_emails(user_id, campaign_id=campaign_id, limit=5000)
        processed_lead_ids = {e.lead_id for e in existing_emails if e.follow_up_step == 0}
        return [l for l in saved_with_email if l.id not in processed_lead_ids]

    def _find_due_followups(self, user_id: int, campaign_id: int):
        now = datetime.now(UTC)
        emails = self.repo.list_outreach_emails(user_id, campaign_id=campaign_id, limit=500)
        return [
            e
            for e in emails
            if e.is_follow_up
            and e.status == OutreachEmailStatus.queued
            and e.scheduled_at
            and as_utc(e.scheduled_at) <= now
        ]

    def _find_first_lead_for_pilot(self, user_id: int, campaign_id: int) -> Lead | None:
        todays = self._find_todays_unprocessed_leads(user_id, campaign_id)
        if todays:
            return todays[0]
        saved = self._find_unprocessed_saved_leads(user_id, campaign_id)
        return saved[0] if saved else None

    def _run_pilot_email(self, user_id: int, campaign_id: int) -> dict | None:
        """Immediately generate + queue one test email so user sees agent is working."""
        lead = self._find_first_lead_for_pilot(user_id, campaign_id)
        if not lead:
            self._log(user_id, "pilot_skipped", "No leads with email for pilot outreach", level="warn")
            return None

        if not lead.is_saved:
            lead.is_saved = True
            lead.saved_at = datetime.now(UTC)
            self.db.commit()

        if not self.process_single_lead(user_id, lead, campaign_id, pilot=True):
            return None

        row = next(
            (
                e
                for e in self.repo.list_outreach_emails(user_id, campaign_id=campaign_id, limit=200)
                if e.lead_id == lead.id and e.follow_up_step == 0
            ),
            None,
        )
        if not row:
            return None

        self._log(
            user_id,
            "pilot_email",
            f"Pilot email to {row.to_email}: {row.subject}",
            lead_id=lead.id,
        )
        self.notifications.notify(
            user_id,
            NotificationType.email_sent,
            f"Pilot email: {lead.company_name or row.to_email}",
            f"To: {row.to_email}\nSubject: {row.subject}",
            lead_id=lead.id,
        )
        return {
            "lead_id": lead.id,
            "company_name": lead.company_name,
            "to_email": row.to_email,
            "subject": row.subject,
            "body_text": row.body_text,
            "status": row.status.value if hasattr(row.status, "value") else str(row.status),
        }

    def process_single_lead(
        self, user_id: int, lead: Lead, campaign_id: int, *, pilot: bool = False
    ) -> bool:
        settings = self.repo.get_or_create_settings(user_id)
        if not lead.email:
            return False

        existing = next(
            (
                e
                for e in self.repo.list_outreach_emails(user_id, campaign_id=campaign_id, limit=1000)
                if e.lead_id == lead.id and e.follow_up_step == 0
            ),
            None,
        )
        if existing:
            return False

        result = verify_outreach_email(lead.email, lead.website)
        self.repo.add_timeline_event(
            {
                "user_id": user_id,
                "lead_id": lead.id,
                "event_type": (
                    EmailTimelineEventType.email_verified
                    if can_send_to_email(result)
                    else EmailTimelineEventType.status_changed
                ),
                "description": (
                    f"Email verified: {result.email}"
                    if can_send_to_email(result)
                    else f"Email verification failed: {', '.join(result.reasons)}"
                ),
                "event_meta": result.to_dict(),
            }
        )

        if not can_send_to_email(result):
            lead.email_verified = False
            self._log(
                user_id,
                "email_skipped",
                f"Skipped {lead.company_name} — invalid email",
                lead_id=lead.id,
                level="warn",
            )
            self.db.commit()
            return False

        lead.email_verified = True
        gen = EmailGenerationService(self.db, user_id)
        subject, body = gen.generate(lead)

        require_review = settings.require_review and not pilot
        email_status = OutreachEmailStatus.queued if pilot else (
            OutreachEmailStatus.pending_review if require_review else OutreachEmailStatus.queued
        )
        if not pilot and not require_review and settings.auto_send_enabled:
            email_status = OutreachEmailStatus.queued

        campaign = self.repo.get_campaign(user_id, campaign_id)
        row = self.repo.create_outreach_email(
            {
                "user_id": user_id,
                "outreach_campaign_id": campaign_id,
                "lead_id": lead.id,
                "email_account_id": campaign.email_account_id if campaign else None,
                "follow_up_step": 0,
                "to_email": result.email,
                "subject": subject,
                "body_text": body,
                "status": email_status,
                "verification_status": "verified",
                "verification_details": result.to_dict(),
                "tracking_token": secrets.token_urlsafe(16),
                "ai_generated": True,
            }
        )

        settings.ai_emails_generated += 1
        self.repo.add_timeline_event(
            {
                "user_id": user_id,
                "lead_id": lead.id,
                "outreach_email_id": row.id,
                "event_type": EmailTimelineEventType.ai_email_generated,
                "description": f"AI email generated: {subject}",
            }
        )
        self._log(
            user_id,
            "email_generated",
            f"Generated email for {lead.company_name}",
            lead_id=lead.id,
        )

        if email_status == OutreachEmailStatus.queued:
            self.queue.enqueue(
                user_id,
                OutreachJobType.send_email,
                {"outreach_email_id": row.id, "pilot": pilot},
                idempotency_key=f"send_{row.id}",
                priority=30 if pilot else 10,
            )

        if lead.status == LeadStatus.new:
            self.lead_repo.update(lead, {"status": LeadStatus.contacted})

        self.notifications.notify(
            user_id,
            NotificationType.lead_processed,
            f"Lead processed: {lead.company_name}",
            f"AI email {'queued' if email_status == OutreachEmailStatus.queued else 'pending review'} for {result.email}",
            lead_id=lead.id,
        )
        self.db.commit()
        return True

    def schedule_followups_for_lead(
        self, user_id: int, lead_id: int, campaign_id: int, initial_email
    ) -> int:
        settings = self.repo.get_or_create_settings(user_id)
        if not settings.auto_follow_up:
            return 0

        steps = [
            s
            for s in self.repo.get_follow_up_steps(campaign_id)
            if s.step_number > 0 and s.is_active
        ]
        scheduled = 0
        lead = self.lead_repo.get_by_id(user_id, lead_id)
        if not lead:
            return 0

        for step in steps:
            existing = next(
                (
                    e
                    for e in self.repo.list_outreach_emails(user_id, campaign_id=campaign_id, limit=500)
                    if e.lead_id == lead_id and e.follow_up_step == step.step_number
                ),
                None,
            )
            if existing:
                continue

            scheduled_at = (initial_email.sent_at or datetime.now(UTC)) + timedelta(
                days=step.delay_days
            )
            gen = EmailGenerationService(self.db, user_id)
            subject, body = gen.generate(
                lead,
                is_follow_up=True,
                follow_up_number=step.step_number,
                previous_subject=initial_email.subject,
            )
            if step.subject_override:
                subject = step.subject_override

            row = self.repo.create_outreach_email(
                {
                    "user_id": user_id,
                    "outreach_campaign_id": campaign_id,
                    "lead_id": lead_id,
                    "email_account_id": initial_email.email_account_id,
                    "follow_up_step": step.step_number,
                    "to_email": initial_email.to_email,
                    "subject": subject,
                    "body_text": body,
                    "status": OutreachEmailStatus.queued,
                    "scheduled_at": scheduled_at,
                    "thread_id": initial_email.thread_id,
                    "in_reply_to": initial_email.external_message_id,
                    "ai_generated": True,
                    "is_follow_up": True,
                }
            )
            self.repo.add_timeline_event(
                {
                    "user_id": user_id,
                    "lead_id": lead_id,
                    "outreach_email_id": row.id,
                    "event_type": EmailTimelineEventType.follow_up_scheduled,
                    "description": f"Follow-up #{step.step_number} scheduled for {scheduled_at.date()}",
                }
            )
            scheduled += 1

        self.db.commit()
        return scheduled

    def list_activity(self, user_id: int, limit: int = 50) -> list[AgentActivityLog]:
        return (
            self.db.query(AgentActivityLog)
            .filter(AgentActivityLog.user_id == user_id)
            .order_by(AgentActivityLog.created_at.desc())
            .limit(limit)
            .all()
        )
