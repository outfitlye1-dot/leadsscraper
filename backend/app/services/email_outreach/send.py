"""Send outreach emails with rate limits and safety checks."""

from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.email_outreach import (
    EmailAccountStatus,
    EmailTimelineEventType,
    NotificationType,
    OutreachEmailStatus,
)
from app.models.lead import LeadStatus
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.repositories.lead_repository import LeadRepository
from app.services.email_outreach.agent import AiOutreachAgent
from app.services.email_outreach.notifications import NotificationService
from app.services.email_outreach.transport import EmailTransportError, refresh_oauth_token, send_email
from app.services.email_outreach.verification import can_send_to_email, verify_outreach_email
from app.utils.datetime_utils import as_utc


class EmailSendService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)
        self.lead_repo = LeadRepository(db)
        self._last_send_times: dict[int, list[float]] = {}

    def _check_limits(self, user_id: int, account_id: int | None, *, pilot: bool = False) -> str | None:
        settings = self.repo.get_or_create_settings(user_id)
        if not pilot and not settings.automation_enabled:
            return "Automation is disabled"

        agent = AiOutreachAgent(self.db)
        if not pilot and not agent.is_within_working_hours(settings):
            return "Outside configured working hours"

        daily = self.repo.count_sent_today(user_id, account_id)
        if daily >= settings.daily_send_limit:
            return f"Daily send limit reached ({settings.daily_send_limit})"

        hourly = self.repo.count_sent_last_hour(user_id)
        if hourly >= settings.hourly_send_limit:
            return f"Hourly send limit reached ({settings.hourly_send_limit})"

        now = time.time()
        times = [t for t in self._last_send_times.get(user_id, []) if now - t < 60]
        if len(times) >= settings.rate_limit_per_minute:
            return "Rate limit exceeded — try again shortly"
        self._last_send_times[user_id] = times
        return None

    def _record_send(self, user_id: int) -> None:
        self._last_send_times.setdefault(user_id, []).append(time.time())

    def _ensure_token_fresh(self, account) -> None:
        if account.oauth_expires_at and as_utc(account.oauth_expires_at) <= datetime.now(UTC):
            if not refresh_oauth_token(account):
                raise EmailTransportError("Failed to refresh OAuth token")
            self.db.commit()

    def send_outreach_email(
        self, user_id: int, outreach_email_id: int, *, pilot: bool = False
    ) -> OutreachEmailStatus:
        row = self.repo.get_outreach_email(user_id, outreach_email_id)
        if not row:
            raise ValueError("Outreach email not found")

        if row.status in (
            OutreachEmailStatus.sent,
            OutreachEmailStatus.delivered,
            OutreachEmailStatus.replied,
            OutreachEmailStatus.cancelled,
        ):
            return row.status

        if not pilot and row.scheduled_at:
            due_at = as_utc(row.scheduled_at)
            if due_at and due_at > datetime.now(UTC):
                return OutreachEmailStatus.queued

        lead = self.lead_repo.get_by_id(user_id, row.lead_id)
        if not lead:
            raise ValueError("Lead not found")

        verification = verify_outreach_email(row.to_email, lead.website)
        if not can_send_to_email(verification):
            self.repo.update_outreach_email(
                row,
                {
                    "status": OutreachEmailStatus.verification_failed,
                    "verification_status": "failed",
                    "verification_details": verification.to_dict(),
                    "error_message": "Email failed verification — will not send",
                },
            )
            return OutreachEmailStatus.verification_failed

        account = None
        if row.email_account_id:
            account = self.repo.get_account(user_id, row.email_account_id)
        if not account:
            account = self.repo.get_default_account(user_id)
        if not account or account.status != EmailAccountStatus.connected:
            self.repo.update_outreach_email(
                row,
                {
                    "status": OutreachEmailStatus.failed,
                    "error_message": "No connected email account",
                },
            )
            raise EmailTransportError("No connected email account")

        limit_error = self._check_limits(user_id, account.id, pilot=pilot)
        if limit_error:
            self.repo.update_outreach_email(
                row,
                {"status": OutreachEmailStatus.queued, "error_message": limit_error},
            )
            raise EmailTransportError(limit_error)

        settings = self.repo.get_or_create_settings(user_id)
        body_text = row.body_text
        if settings.include_unsubscribe:
            body_text += (
                "\n\n—\nIf you'd rather not hear from me again, just reply 'unsubscribe'."
            )

        self._ensure_token_fresh(account)
        self.repo.update_outreach_email(row, {"status": OutreachEmailStatus.sending})

        try:
            message_id = send_email(
                account,
                row.to_email,
                row.subject,
                body_text,
                row.body_html,
                in_reply_to=row.in_reply_to,
            )
        except EmailTransportError as exc:
            self.repo.update_account(account, {"status": EmailAccountStatus.error, "last_error": str(exc)})
            self.repo.update_outreach_email(
                row,
                {"status": OutreachEmailStatus.failed, "error_message": str(exc)},
            )
            raise

        now = datetime.now(UTC)
        tracking_token = row.tracking_token or secrets.token_urlsafe(16)
        self.repo.update_outreach_email(
            row,
            {
                "status": OutreachEmailStatus.sent,
                "external_message_id": message_id,
                "thread_id": row.thread_id or message_id,
                "tracking_token": tracking_token,
                "sent_at": now,
                "delivered_at": now,
                "email_account_id": account.id,
                "error_message": None,
            },
        )

        account.daily_sent_count += 1
        account.updated_at = now
        self.db.commit()

        if lead.status == LeadStatus.new:
            self.lead_repo.update(lead, {"status": LeadStatus.contacted})
        lead.email_verified = True
        self.db.commit()

        self.repo.add_timeline_event(
            {
                "user_id": user_id,
                "lead_id": lead.id,
                "outreach_email_id": row.id,
                "event_type": EmailTimelineEventType.email_sent,
                "description": f"Email sent: {row.subject}",
                "event_meta": {"to": row.to_email},
            }
        )
        self.repo.add_timeline_event(
            {
                "user_id": user_id,
                "lead_id": lead.id,
                "outreach_email_id": row.id,
                "event_type": EmailTimelineEventType.delivered,
                "description": "Email delivered",
            }
        )

        if row.is_follow_up:
            self.repo.add_timeline_event(
                {
                    "user_id": user_id,
                    "lead_id": lead.id,
                    "outreach_email_id": row.id,
                    "event_type": EmailTimelineEventType.follow_up_sent,
                    "description": f"Follow-up #{row.follow_up_step} sent",
                }
            )
        elif row.follow_up_step == 0 and settings.auto_follow_up:
            AiOutreachAgent(self.db).schedule_followups_for_lead(
                user_id, lead.id, row.outreach_campaign_id, row
            )

        NotificationService(self.db).notify(
            user_id,
            NotificationType.email_sent,
            f"Email sent to {lead.company_name or row.to_email}",
            row.subject,
            lead_id=lead.id,
        )

        self._record_send(user_id)
        return OutreachEmailStatus.sent
