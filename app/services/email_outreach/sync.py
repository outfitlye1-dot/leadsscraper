"""Inbox synchronization for connected email accounts."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.email_outreach import EmailAccountStatus, EmailConversation, OutreachEmail
from app.models.lead import Lead
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.services.email_outreach.reply import ReplyService
from app.services.email_outreach.transport import fetch_inbox_messages, refresh_oauth_token
from app.utils.datetime_utils import as_utc


class InboxSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)
        self.reply_service = ReplyService(db)

    def _known_contact_emails(self, user_id: int) -> list[str]:
        """Emails we expect replies from (active chats first, then outreach)."""
        from app.models.email_outreach import ConversationMessage

        ordered: list[str] = []
        seen: set[str] = set()

        def add(addr: str | None) -> None:
            if not addr or "@" not in addr:
                return
            key = addr.strip().lower()
            if key in seen:
                return
            seen.add(key)
            ordered.append(key)

        for conv in (
            self.db.query(EmailConversation)
            .filter(EmailConversation.user_id == user_id)
            .order_by(EmailConversation.last_message_at.desc().nullslast())
            .limit(40)
            .all()
        ):
            lead = self.db.query(Lead).filter(
                Lead.id == conv.lead_id, Lead.user_id == user_id
            ).first()
            add(lead.email if lead else None)

        for (to_email,) in (
            self.db.query(ConversationMessage.to_email)
            .join(EmailConversation, EmailConversation.id == ConversationMessage.conversation_id)
            .filter(
                EmailConversation.user_id == user_id,
                ConversationMessage.direction == "outbound",
            )
            .order_by(ConversationMessage.received_at.desc())
            .limit(40)
            .all()
        ):
            add(to_email)

        for (email,) in (
            self.db.query(OutreachEmail.to_email)
            .filter(OutreachEmail.user_id == user_id)
            .order_by(OutreachEmail.created_at.desc())
            .limit(40)
            .all()
        ):
            add(email)

        return ordered[:25]

    def sync_account(
        self, user_id: int, account_id: int, *, focus_email: str | None = None
    ) -> dict:
        account = self.repo.get_account(user_id, account_id)
        if not account:
            return {"error": "account_not_found"}

        # Debounce chat polling — short so Gmail replies appear quickly without pile-up
        if account.last_sync_at:
            age = (datetime.now(UTC) - as_utc(account.last_sync_at)).total_seconds()
            if age < 5:
                return {
                    "synced": 0,
                    "matched_replies": 0,
                    "new_replies": 0,
                    "skipped": True,
                }

        try:
            expires = as_utc(account.oauth_expires_at) if account.oauth_expires_at else None
            now = datetime.now(UTC)
            # Only refresh when expired / about to expire — avoid slowing every chat sync
            needs_refresh = expires is None or expires <= now or (expires - now).total_seconds() < 300
            if needs_refresh:
                from app.models.email_outreach import EmailProvider

                if account.provider in (EmailProvider.gmail_oauth, EmailProvider.outlook_oauth):
                    refresh_oauth_token(account)
                    self.db.commit()
        except Exception:
            pass

        contact_emails = self._known_contact_emails(user_id)
        focus = (focus_email or "").strip().lower()
        if focus and "@" in focus:
            contact_emails = [focus] + [e for e in contact_emails if e != focus]
        # Keep IMAP FROM searches small — focused / chat contacts first
        messages = fetch_inbox_messages(
            account,
            limit=20,
            from_emails=contact_emails[:6],
        )
        processed = 0
        new_replies = 0
        for msg in messages:
            try:
                result = self.reply_service.process_inbound_message(
                    user_id,
                    from_email=msg.get("from_email", ""),
                    to_email=msg.get("to_email", account.email_address),
                    subject=msg.get("subject", ""),
                    body_text=msg.get("body_text", ""),
                    message_id=msg.get("message_id"),
                    in_reply_to=msg.get("in_reply_to"),
                    # Chat sync is on the request path — never block on Groq here
                    skip_ai=True,
                )
            except Exception:
                # Never abort the whole inbox sync on one bad message
                self.db.rollback()
                continue
            if result.get("matched") and not result.get("duplicate"):
                processed += 1
                new_replies += 1
            elif result.get("matched"):
                processed += 1

        self.repo.update_account(
            account,
            {
                "last_sync_at": datetime.now(UTC),
                "status": EmailAccountStatus.connected,
                "last_error": None,
            },
        )
        return {
            "synced": len(messages),
            "matched_replies": processed,
            "new_replies": new_replies,
        }

    def sync_all_for_user(
        self, user_id: int, *, focus_email: str | None = None
    ) -> dict:
        accounts = self.repo.list_accounts(user_id)
        total = 0
        matched = 0
        new_replies = 0
        for account in accounts:
            if account.status == EmailAccountStatus.connected:
                result = self.sync_account(
                    user_id, account.id, focus_email=focus_email
                )
                total += result.get("synced", 0)
                matched += result.get("matched_replies", 0)
                new_replies += result.get("new_replies", 0)
        return {
            "synced": total,
            "matched_replies": matched,
            "new_replies": new_replies,
        }
