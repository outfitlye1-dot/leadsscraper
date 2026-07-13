"""Inbox synchronization for connected email accounts."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.email_outreach import EmailAccountStatus
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.services.email_outreach.reply import ReplyService
from app.services.email_outreach.transport import fetch_inbox_messages, refresh_oauth_token
from app.utils.datetime_utils import as_utc


class InboxSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)
        self.reply_service = ReplyService(db)

    def sync_account(self, user_id: int, account_id: int) -> dict:
        account = self.repo.get_account(user_id, account_id)
        if not account:
            return {"error": "account_not_found"}

        if account.oauth_expires_at and as_utc(account.oauth_expires_at) <= datetime.now(UTC):
            refresh_oauth_token(account)
            self.db.commit()

        messages = fetch_inbox_messages(account, limit=30)
        processed = 0
        for msg in messages:
            result = self.reply_service.process_inbound_message(
                user_id,
                from_email=msg.get("from_email", ""),
                to_email=msg.get("to_email", account.email_address),
                subject=msg.get("subject", ""),
                body_text=msg.get("body_text", ""),
                message_id=msg.get("message_id"),
                in_reply_to=msg.get("in_reply_to"),
            )
            if result.get("matched"):
                processed += 1

        self.repo.update_account(
            account,
            {
                "last_sync_at": datetime.now(UTC),
                "status": EmailAccountStatus.connected,
                "last_error": None,
            },
        )
        return {"synced": len(messages), "matched_replies": processed}

    def sync_all_for_user(self, user_id: int) -> dict:
        accounts = self.repo.list_accounts(user_id)
        total = 0
        matched = 0
        for account in accounts:
            if account.status == EmailAccountStatus.connected:
                result = self.sync_account(user_id, account.id)
                total += result.get("synced", 0)
                matched += result.get("matched_replies", 0)
        return {"synced": total, "matched_replies": matched}
