"""Data access for email outreach."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.email_outreach import (
    AiReplyDraft,
    EmailAccount,
    EmailConversation,
    EmailOutreachCampaign,
    EmailOutreachSettings,
    EmailTimelineEvent,
    FollowUpStep,
    OutreachEmail,
    OutreachJob,
)


class EmailOutreachRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_settings(self, user_id: int) -> EmailOutreachSettings | None:
        return (
            self.db.query(EmailOutreachSettings)
            .filter(EmailOutreachSettings.user_id == user_id)
            .first()
        )

    def get_or_create_settings(self, user_id: int) -> EmailOutreachSettings:
        settings = self.get_settings(user_id)
        if settings:
            return settings
        settings = EmailOutreachSettings(user_id=user_id)
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def list_accounts(self, user_id: int) -> list[EmailAccount]:
        return (
            self.db.query(EmailAccount)
            .filter(EmailAccount.user_id == user_id)
            .order_by(EmailAccount.is_default.desc(), EmailAccount.created_at.desc())
            .all()
        )

    def get_account(self, user_id: int, account_id: int) -> EmailAccount | None:
        return (
            self.db.query(EmailAccount)
            .filter(EmailAccount.user_id == user_id, EmailAccount.id == account_id)
            .first()
        )

    def get_default_account(self, user_id: int) -> EmailAccount | None:
        settings = self.get_settings(user_id)
        if settings and settings.default_email_account_id:
            account = self.get_account(user_id, settings.default_email_account_id)
            if account:
                return account
        return (
            self.db.query(EmailAccount)
            .filter(EmailAccount.user_id == user_id, EmailAccount.is_default.is_(True))
            .first()
        )

    def create_account(self, user_id: int, data: dict) -> EmailAccount:
        account = EmailAccount(user_id=user_id, **data)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update_account(self, account: EmailAccount, data: dict) -> EmailAccount:
        for key, value in data.items():
            setattr(account, key, value)
        account.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete_account(self, account: EmailAccount) -> None:
        self.db.delete(account)
        self.db.commit()

    def list_campaigns(self, user_id: int) -> list[EmailOutreachCampaign]:
        return (
            self.db.query(EmailOutreachCampaign)
            .filter(EmailOutreachCampaign.user_id == user_id)
            .order_by(EmailOutreachCampaign.created_at.desc())
            .all()
        )

    def get_campaign(self, user_id: int, campaign_id: int) -> EmailOutreachCampaign | None:
        return (
            self.db.query(EmailOutreachCampaign)
            .filter(
                EmailOutreachCampaign.user_id == user_id,
                EmailOutreachCampaign.id == campaign_id,
            )
            .first()
        )

    def create_campaign(self, user_id: int, data: dict) -> EmailOutreachCampaign:
        campaign = EmailOutreachCampaign(user_id=user_id, **data)
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def update_campaign(self, campaign: EmailOutreachCampaign, data: dict) -> EmailOutreachCampaign:
        for key, value in data.items():
            setattr(campaign, key, value)
        campaign.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def set_follow_up_steps(self, campaign_id: int, steps: list[dict]) -> list[FollowUpStep]:
        self.db.query(FollowUpStep).filter(FollowUpStep.outreach_campaign_id == campaign_id).delete()
        created: list[FollowUpStep] = []
        for step in steps:
            row = FollowUpStep(outreach_campaign_id=campaign_id, **step)
            self.db.add(row)
            created.append(row)
        self.db.commit()
        return created

    def get_follow_up_steps(self, campaign_id: int) -> list[FollowUpStep]:
        return (
            self.db.query(FollowUpStep)
            .filter(FollowUpStep.outreach_campaign_id == campaign_id)
            .order_by(FollowUpStep.step_number.asc())
            .all()
        )

    def create_outreach_email(self, data: dict) -> OutreachEmail:
        row = OutreachEmail(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_outreach_email(self, user_id: int, email_id: int) -> OutreachEmail | None:
        return (
            self.db.query(OutreachEmail)
            .filter(OutreachEmail.user_id == user_id, OutreachEmail.id == email_id)
            .first()
        )

    def list_outreach_emails(
        self,
        user_id: int,
        *,
        campaign_id: int | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[OutreachEmail]:
        q = self.db.query(OutreachEmail).filter(OutreachEmail.user_id == user_id)
        if campaign_id:
            q = q.filter(OutreachEmail.outreach_campaign_id == campaign_id)
        if status:
            q = q.filter(OutreachEmail.status == status)
        return q.order_by(OutreachEmail.created_at.desc()).limit(limit).all()

    def update_outreach_email(self, row: OutreachEmail, data: dict) -> OutreachEmail:
        for key, value in data.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(row)
        return row

    def add_timeline_event(self, data: dict) -> EmailTimelineEvent:
        event = EmailTimelineEvent(**data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_timeline(self, user_id: int, lead_id: int, limit: int = 50) -> list[EmailTimelineEvent]:
        return (
            self.db.query(EmailTimelineEvent)
            .filter(EmailTimelineEvent.user_id == user_id, EmailTimelineEvent.lead_id == lead_id)
            .order_by(EmailTimelineEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_conversation(self, user_id: int, conversation_id: int) -> EmailConversation | None:
        return (
            self.db.query(EmailConversation)
            .filter(
                EmailConversation.user_id == user_id,
                EmailConversation.id == conversation_id,
            )
            .first()
        )

    def list_conversations(self, user_id: int, limit: int = 50) -> list[EmailConversation]:
        return (
            self.db.query(EmailConversation)
            .filter(EmailConversation.user_id == user_id)
            .order_by(EmailConversation.last_message_at.desc().nullslast())
            .limit(limit)
            .all()
        )

    def create_conversation(self, data: dict) -> EmailConversation:
        row = EmailConversation(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_ai_drafts(self, user_id: int, limit: int = 50) -> list[AiReplyDraft]:
        from app.models.email_outreach import AiReplyDraftStatus

        return (
            self.db.query(AiReplyDraft)
            .filter(
                AiReplyDraft.user_id == user_id,
                AiReplyDraft.status == AiReplyDraftStatus.pending_approval,
            )
            .order_by(AiReplyDraft.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_ai_draft(self, user_id: int, draft_id: int) -> AiReplyDraft | None:
        return (
            self.db.query(AiReplyDraft)
            .filter(AiReplyDraft.user_id == user_id, AiReplyDraft.id == draft_id)
            .first()
        )

    def count_sent_today(self, user_id: int, account_id: int | None = None) -> int:
        from app.models.email_outreach import OutreachEmailStatus

        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        q = self.db.query(OutreachEmail).filter(
            OutreachEmail.user_id == user_id,
            OutreachEmail.sent_at >= today,
            OutreachEmail.status.in_(
                [
                    OutreachEmailStatus.sent,
                    OutreachEmailStatus.delivered,
                    OutreachEmailStatus.opened,
                    OutreachEmailStatus.replied,
                ]
            ),
        )
        if account_id:
            q = q.filter(OutreachEmail.email_account_id == account_id)
        return q.count()

    def count_sent_last_hour(self, user_id: int) -> int:
        from datetime import timedelta
        from app.models.email_outreach import OutreachEmailStatus

        cutoff = datetime.now(UTC) - timedelta(hours=1)
        return (
            self.db.query(OutreachEmail)
            .filter(
                OutreachEmail.user_id == user_id,
                OutreachEmail.sent_at >= cutoff,
                OutreachEmail.status.in_(
                    [
                        OutreachEmailStatus.sent,
                        OutreachEmailStatus.delivered,
                        OutreachEmailStatus.opened,
                        OutreachEmailStatus.replied,
                    ]
                ),
            )
            .count()
        )
