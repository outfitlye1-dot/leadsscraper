"""Enhanced dashboard statistics for outreach."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.email_outreach import (
    AgentActivityLog,
    ConversationStatus,
    EmailAccountStatus,
    OutreachCampaignStatus,
    OutreachEmail,
    OutreachEmailStatus,
    OutreachJob,
    OutreachJobStatus,
    ReplyIntent,
)
from app.models.lead import Lead, LeadStatus
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.services.email_outreach.agent import AiOutreachAgent


SENT_STATUSES = {
    OutreachEmailStatus.sent,
    OutreachEmailStatus.delivered,
    OutreachEmailStatus.opened,
    OutreachEmailStatus.replied,
}


class OutreachDashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)

    def _count_sent_since(self, user_id: int, since: datetime) -> int:
        return (
            self.db.query(OutreachEmail)
            .filter(
                OutreachEmail.user_id == user_id,
                OutreachEmail.sent_at >= since,
                OutreachEmail.status.in_(list(SENT_STATUSES)),
            )
            .count()
        )

    def build_stats(self, user_id: int) -> dict:
        settings = self.repo.get_or_create_settings(user_id)
        accounts = self.repo.list_accounts(user_id)
        campaigns = self.repo.list_campaigns(user_id)
        emails = self.repo.list_outreach_emails(user_id, limit=10000)
        agent = AiOutreachAgent(self.db)

        now = datetime.now(UTC)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        sent = [e for e in emails if e.status in SENT_STATUSES]
        delivered = [e for e in sent if e.delivered_at]
        opened = [e for e in sent if e.opened_at]
        replied = [e for e in sent if e.replied_at]
        bounced = [e for e in emails if e.status == OutreachEmailStatus.bounced]
        failed = [e for e in emails if e.status == OutreachEmailStatus.failed]
        queued = [e for e in emails if e.status == OutreachEmailStatus.queued]
        pending = [
            e
            for e in emails
            if e.status
            in (
                OutreachEmailStatus.pending_review,
                OutreachEmailStatus.pending_verification,
                OutreachEmailStatus.draft,
            )
        ]
        follow_up_queue = len([e for e in queued if e.is_follow_up])
        follow_ups_scheduled = len(
            [e for e in emails if e.is_follow_up and e.status == OutreachEmailStatus.queued]
        )
        follow_ups_completed = len(
            [e for e in emails if e.is_follow_up and e.status in SENT_STATUSES]
        )

        conversations = self.repo.list_conversations(user_id, limit=500)
        positive_replies = len(
            [
                c
                for c in conversations
                if c.reply_intent in (ReplyIntent.interested, ReplyIntent.meeting_request)
            ]
        )
        interested = (
            self.db.query(Lead)
            .filter(Lead.user_id == user_id, Lead.status == LeadStatus.interested)
            .count()
        )
        meetings = len(
            [c for c in conversations if c.reply_intent == ReplyIntent.meeting_request]
        )

        sent_lead_ids = {e.lead_id for e in sent}
        replied_lead_ids = {e.lead_id for e in replied}
        no_response = len(sent_lead_ids - replied_lead_ids)

        sent_count = len(sent)
        open_rate = (len(opened) / sent_count * 100) if sent_count else 0.0
        reply_rate = (len(replied) / sent_count * 100) if sent_count else 0.0
        bounce_rate = (len(bounced) / sent_count * 100) if sent_count else 0.0
        success_rate = (len(delivered) / sent_count * 100) if sent_count else 0.0
        conversion_rate = (interested / sent_count * 100) if sent_count else 0.0

        pending_jobs = (
            self.db.query(OutreachJob)
            .filter(
                OutreachJob.user_id == user_id,
                OutreachJob.status == OutreachJobStatus.pending,
            )
            .count()
        )
        running_jobs = (
            self.db.query(OutreachJob)
            .filter(
                OutreachJob.user_id == user_id,
                OutreachJob.status == OutreachJobStatus.running,
            )
            .count()
        )

        default_account = self.repo.get_default_account(user_id)
        sent_today = self.repo.count_sent_today(user_id)

        activity_rows = (
            self.db.query(AgentActivityLog)
            .filter(AgentActivityLog.user_id == user_id)
            .order_by(AgentActivityLog.created_at.desc())
            .limit(15)
            .all()
        )
        recent_activity = [
            {
                "id": a.id,
                "type": a.activity_type,
                "message": a.message,
                "level": a.level,
                "lead_id": a.lead_id,
                "created_at": a.created_at.isoformat(),
            }
            for a in activity_rows
        ]

        recent_replies = [
            {
                "conversation_id": c.id,
                "lead_id": c.lead_id,
                "intent": c.reply_intent.value if c.reply_intent else None,
                "summary": c.reply_summary,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            }
            for c in sorted(
                [c for c in conversations if c.status == ConversationStatus.responded],
                key=lambda x: x.last_message_at or x.created_at,
                reverse=True,
            )[:10]
        ]

        upcoming_followups = [
            {
                "id": e.id,
                "lead_id": e.lead_id,
                "subject": e.subject,
                "scheduled_at": e.scheduled_at.isoformat() if e.scheduled_at else None,
                "follow_up_step": e.follow_up_step,
            }
            for e in sorted(
                [e for e in queued if e.is_follow_up and e.scheduled_at],
                key=lambda x: x.scheduled_at,
            )[:10]
        ]

        ai_tokens = (settings.ai_emails_generated + settings.ai_replies_generated) * 450
        estimated_cost = round(ai_tokens * 0.0000005, 4)

        return {
            "connected_accounts": len(
                [a for a in accounts if a.status == EmailAccountStatus.connected]
            ),
            "active_campaigns": len(
                [
                    c
                    for c in campaigns
                    if c.status
                    in (
                        OutreachCampaignStatus.active,
                        OutreachCampaignStatus.sending,
                        OutreachCampaignStatus.review,
                    )
                ]
            ),
            "emails_sent": sent_count,
            "emails_delivered": len(delivered),
            "open_rate": round(open_rate, 1),
            "reply_rate": round(reply_rate, 1),
            "bounce_rate": round(bounce_rate, 1),
            "follow_up_queue": follow_up_queue,
            "pending_ai_drafts": len(self.repo.list_ai_drafts(user_id)),
            "automation_enabled": settings.automation_enabled,
            "pending_jobs": pending_jobs,
            "emails_sent_today": self._count_sent_since(user_id, today),
            "emails_sent_this_week": self._count_sent_since(user_id, week_ago),
            "emails_sent_this_month": self._count_sent_since(user_id, month_ago),
            "pending_emails": len(pending),
            "failed_emails": len(failed),
            "queued_emails": len(queued),
            "replies_received": len(replied),
            "positive_replies": positive_replies,
            "interested_leads": interested,
            "meetings_requested": meetings,
            "follow_ups_scheduled": follow_ups_scheduled,
            "follow_ups_completed": follow_ups_completed,
            "no_response_leads": no_response,
            "completed_campaigns": len(
                [c for c in campaigns if c.status == OutreachCampaignStatus.completed]
            ),
            "running_campaigns": len(
                [
                    c
                    for c in campaigns
                    if c.status
                    in (OutreachCampaignStatus.active, OutreachCampaignStatus.sending)
                ]
            ),
            "paused_campaigns": len(
                [c for c in campaigns if c.status == OutreachCampaignStatus.paused]
            ),
            "ai_emails_generated": settings.ai_emails_generated,
            "ai_replies_generated": settings.ai_replies_generated,
            "ai_tokens_used": ai_tokens,
            "estimated_ai_cost": estimated_cost,
            "gmail_connected": bool(
                default_account and default_account.status == EmailAccountStatus.connected
            ),
            "gmail_email": default_account.email_address if default_account else None,
            "daily_sending_limit": settings.daily_send_limit,
            "emails_remaining_today": max(0, settings.daily_send_limit - sent_today),
            "sync_status": (
                default_account.status.value
                if default_account
                else "disconnected"
            ),
            "last_sync_time": default_account.last_sync_at if default_account else None,
            "agent_running": settings.agent_running,
            "agent_paused": settings.agent_paused,
            "last_agent_run_at": settings.last_agent_run_at,
            "within_working_hours": agent.is_within_working_hours(settings),
            "success_rate": round(success_rate, 1),
            "conversion_rate": round(conversion_rate, 1),
            "recent_activity": recent_activity,
            "recent_replies": recent_replies,
            "upcoming_followups": upcoming_followups,
            "running_jobs": running_jobs,
        }
