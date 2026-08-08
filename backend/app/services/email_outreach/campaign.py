"""Full email outreach campaign workflow orchestration."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.email_outreach import (
    OutreachCampaignStatus,
    OutreachEmailStatus,
    OutreachJobType,
)
from app.models.lead import Lead
from app.models.user import User
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.email_outreach import (
    CampaignLaunchResponse,
    EmailOutreachCampaignCreateRequest,
    EmailOutreachCampaignResponse,
    EmailOutreachCampaignUpdateRequest,
    FollowUpStepResponse,
)
from app.services.email_outreach.generation import EmailGenerationService
from app.utils.datetime_utils import as_utc
from app.services.email_outreach.job_queue import OutreachJobQueue
from app.services.email_outreach.verification import can_send_to_email, verify_outreach_email
from app.utils.secret_encryption import encrypt_json


DEFAULT_FOLLOW_UP_STEPS = [
    {"step_number": 0, "delay_days": 0, "is_active": True},
    {"step_number": 1, "delay_days": 3, "is_active": True},
    {"step_number": 2, "delay_days": 5, "is_active": True},
    {"step_number": 3, "delay_days": 7, "is_active": True},
]


class EmailOutreachCampaignService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)
        self.lead_repo = LeadRepository(db)
        self.queue = OutreachJobQueue(db)

    def _to_response(self, campaign) -> EmailOutreachCampaignResponse:
        steps = self.repo.get_follow_up_steps(campaign.id)
        base = EmailOutreachCampaignResponse.model_validate(campaign)
        base.follow_up_steps = [FollowUpStepResponse.model_validate(s) for s in steps]
        return base

    def create_campaign(
        self, user: User, data: EmailOutreachCampaignCreateRequest
    ) -> EmailOutreachCampaignResponse:
        payload = data.model_dump(exclude={"follow_up_steps"})
        campaign = self.repo.create_campaign(user.id, payload)
        steps = data.follow_up_steps or [dict(s) for s in DEFAULT_FOLLOW_UP_STEPS]
        self.repo.set_follow_up_steps(
            campaign.id,
            [s if isinstance(s, dict) else s.model_dump() for s in steps],
        )
        return self._to_response(campaign)

    def list_campaigns(self, user: User) -> list[EmailOutreachCampaignResponse]:
        return [self._to_response(c) for c in self.repo.list_campaigns(user.id)]

    def get_campaign(self, user: User, campaign_id: int) -> EmailOutreachCampaignResponse:
        campaign = self.repo.get_campaign(user.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return self._to_response(campaign)

    def update_campaign(
        self, user: User, campaign_id: int, data: EmailOutreachCampaignUpdateRequest
    ) -> EmailOutreachCampaignResponse:
        campaign = self.repo.get_campaign(user.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        payload = data.model_dump(exclude_unset=True, exclude={"follow_up_steps"})
        updated = self.repo.update_campaign(campaign, payload)
        if data.follow_up_steps is not None:
            self.repo.set_follow_up_steps(
                campaign_id, [s.model_dump() for s in data.follow_up_steps]
            )
        return self._to_response(updated)

    def _resolve_leads(self, user_id: int, campaign) -> list[Lead]:
        if campaign.lead_ids:
            leads = []
            for lead_id in campaign.lead_ids:
                lead = self.lead_repo.get_by_id(user_id, lead_id)
                if lead:
                    leads.append(lead)
            return leads

        saved_only = campaign.lead_filter_saved_only
        all_leads = self.lead_repo.list_for_campaign_run(user_id, limit=500)
        if saved_only:
            return [l for l in all_leads if l.is_saved and l.email]
        return [l for l in all_leads if l.email]

    def launch_campaign(self, user: User, campaign_id: int) -> CampaignLaunchResponse:
        settings = self.repo.get_or_create_settings(user.id)
        if not settings.automation_enabled:
            raise HTTPException(
                status_code=400,
                detail="Email automation is disabled. Enable it in outreach settings.",
            )

        campaign = self.repo.get_campaign(user.id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        if campaign.status not in (
            OutreachCampaignStatus.draft,
            OutreachCampaignStatus.paused,
        ):
            raise HTTPException(status_code=400, detail=f"Cannot launch campaign in status {campaign.status.value}")

        account = None
        if campaign.email_account_id:
            account = self.repo.get_account(user.id, campaign.email_account_id)
        if not account:
            account = self.repo.get_default_account(user.id)
        if not account:
            raise HTTPException(status_code=400, detail="Connect an email account first")

        self.repo.update_campaign(
            campaign,
            {
                "status": OutreachCampaignStatus.verifying,
                "email_account_id": account.id,
                "started_at": datetime.now(UTC),
            },
        )

        job = self.queue.enqueue(
            user.id,
            OutreachJobType.process_campaign,
            {"campaign_id": campaign_id},
            idempotency_key=f"process_campaign_{campaign_id}",
            priority=10,
        )

        return CampaignLaunchResponse(
            campaign_id=campaign_id,
            status=OutreachCampaignStatus.verifying.value,
            message="Campaign launched — verification and generation queued",
            jobs_enqueued=1 if job else 0,
        )

    def process_campaign(self, user_id: int, campaign_id: int) -> dict:
        campaign = self.repo.get_campaign(user_id, campaign_id)
        if not campaign:
            return {"error": "campaign_not_found"}

        settings = self.repo.get_or_create_settings(user_id)
        require_review = (
            campaign.require_review
            if campaign.require_review is not None
            else settings.require_review
        )

        leads = self._resolve_leads(user_id, campaign)
        verified = 0
        skipped = 0
        generated = 0

        self.repo.update_campaign(campaign, {"status": OutreachCampaignStatus.verifying})
        for lead in leads:
            if not lead.email:
                skipped += 1
                continue

            result = verify_outreach_email(lead.email, lead.website)
            if not can_send_to_email(result):
                skipped += 1
                lead.email_verified = False
                continue

            verified += 1
            lead.email_verified = True

            existing = next(
                (
                    e
                    for e in self.repo.list_outreach_emails(
                        user_id, campaign_id=campaign_id, limit=1000
                    )
                    if e.lead_id == lead.id and e.follow_up_step == 0
                ),
                None,
            )
            if existing:
                continue

            gen = EmailGenerationService(self.db, user_id)
            subject, body = gen.generate(lead)
            status = (
                OutreachEmailStatus.pending_review
                if require_review
                else OutreachEmailStatus.approved
            )
            if not require_review and settings.auto_send_enabled:
                status = OutreachEmailStatus.queued

            row = self.repo.create_outreach_email(
                {
                    "user_id": user_id,
                    "outreach_campaign_id": campaign_id,
                    "lead_id": lead.id,
                    "email_account_id": campaign.email_account_id,
                    "follow_up_step": 0,
                    "to_email": result.email,
                    "subject": subject,
                    "body_text": body,
                    "status": status,
                    "verification_status": "verified",
                    "verification_details": result.to_dict(),
                    "tracking_token": secrets.token_urlsafe(16),
                    "ai_generated": True,
                }
            )
            generated += 1

            if status == OutreachEmailStatus.queued:
                self.queue.enqueue(
                    user_id,
                    OutreachJobType.send_email,
                    {"outreach_email_id": row.id},
                    idempotency_key=f"send_{row.id}",
                )

        self.db.commit()

        next_status = (
            OutreachCampaignStatus.review
            if require_review
            else OutreachCampaignStatus.sending
        )
        self.repo.update_campaign(
            campaign,
            {
                "status": next_status,
                "stats": {
                    "verified": verified,
                    "skipped": skipped,
                    "generated": generated,
                },
            },
        )

        if not require_review and settings.auto_send_enabled:
            self.repo.update_campaign(campaign, {"status": OutreachCampaignStatus.active})

        return {"verified": verified, "skipped": skipped, "generated": generated}

    def approve_email(self, user: User, email_id: int) -> None:
        row = self.repo.get_outreach_email(user.id, email_id)
        if not row:
            raise HTTPException(status_code=404, detail="Email not found")
        if row.status != OutreachEmailStatus.pending_review:
            raise HTTPException(status_code=400, detail="Email is not pending review")

        self.repo.update_outreach_email(row, {"status": OutreachEmailStatus.approved})
        self.queue.enqueue(
            user.id,
            OutreachJobType.send_email,
            {"outreach_email_id": row.id},
            idempotency_key=f"send_{row.id}",
        )

    def schedule_follow_ups(self, user_id: int, campaign_id: int) -> int:
        campaign = self.repo.get_campaign(user_id, campaign_id)
        if not campaign or not campaign.follow_up_enabled:
            return 0

        steps = [s for s in self.repo.get_follow_up_steps(campaign_id) if s.step_number > 0 and s.is_active]
        if not steps:
            return 0

        scheduled = 0
        initial_emails = self.repo.list_outreach_emails(user_id, campaign_id=campaign_id, limit=500)
        initial_emails = [e for e in initial_emails if e.follow_up_step == 0 and e.sent_at]

        for initial in initial_emails:
            if initial.status == OutreachEmailStatus.replied:
                continue

            conv = next(
                (
                    c
                    for c in self.repo.list_conversations(user_id, limit=200)
                    if c.lead_id == initial.lead_id and c.follow_ups_stopped
                ),
                None,
            )
            if conv:
                continue

            for step in steps:
                existing = next(
                    (
                        e
                        for e in initial_emails
                        if e.lead_id == initial.lead_id and e.follow_up_step == step.step_number
                    ),
                    None,
                )
                if existing:
                    continue

                scheduled_at = as_utc(initial.sent_at) + timedelta(days=step.delay_days)
                lead = self.lead_repo.get_by_id(user_id, initial.lead_id)
                if not lead:
                    continue
                gen = EmailGenerationService(self.db, user_id)
                subject, body = gen.generate(
                    lead,
                    is_follow_up=True,
                    follow_up_number=step.step_number,
                    previous_subject=initial.subject,
                )
                if step.subject_override:
                    subject = step.subject_override

                row = self.repo.create_outreach_email(
                    {
                        "user_id": user_id,
                        "outreach_campaign_id": campaign_id,
                        "lead_id": initial.lead_id,
                        "email_account_id": initial.email_account_id,
                        "follow_up_step": step.step_number,
                        "to_email": initial.to_email,
                        "subject": subject,
                        "body_text": body,
                        "status": OutreachEmailStatus.queued,
                        "scheduled_at": scheduled_at,
                        "thread_id": initial.thread_id,
                        "in_reply_to": initial.external_message_id,
                        "ai_generated": True,
                        "is_follow_up": True,
                    }
                )
                self.queue.enqueue(
                    user_id,
                    OutreachJobType.send_email,
                    {"outreach_email_id": row.id},
                    scheduled_at=scheduled_at,
                    idempotency_key=f"followup_{row.id}",
                )
                scheduled += 1

        return scheduled
