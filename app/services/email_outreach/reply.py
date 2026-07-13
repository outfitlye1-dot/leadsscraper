"""Reply detection, intent classification, and AI reply drafts."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.email_outreach import (
    AiReplyDraftStatus,
    ConversationStatus,
    EmailTimelineEventType,
    NotificationType,
    OutreachEmailStatus,
    ReplyIntent,
)
from app.models.lead import LeadStatus
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.repositories.lead_repository import LeadRepository
from app.services.groq_service import GroqService
from app.services.email_outreach.job_queue import OutreachJobQueue
from app.models.email_outreach import OutreachJobType
from app.services.email_outreach.notifications import NotificationService


REPLY_ANALYSIS_PROMPT = """Analyze this email reply from a business lead.

CONVERSATION HISTORY:
{conversation_history}

LATEST REPLY:
{reply_text}

Return ONLY valid JSON:
{{
  "intent": "interested|not_interested|question|meeting_request|unsubscribe|out_of_office|other",
  "summary": "one sentence summary",
  "draft_subject": "suggested reply subject",
  "draft_body": "short helpful reply under 80 words that references conversation context; if discussing pricing, packages are $300–$1,000 USD depending on scope"
}}
"""

SAFE_AUTO_REPLY_INTENTS = {ReplyIntent.question, ReplyIntent.out_of_office}
SKIP_AUTO_REPLY_INTENTS = {ReplyIntent.unsubscribe, ReplyIntent.not_interested}


class ReplyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)
        self.lead_repo = LeadRepository(db)
        self.queue = OutreachJobQueue(db)

    def process_inbound_message(
        self,
        user_id: int,
        *,
        from_email: str,
        to_email: str,
        subject: str,
        body_text: str,
        message_id: str | None = None,
        in_reply_to: str | None = None,
    ) -> dict:
        from_email_clean = self._extract_email(from_email)
        outreach_email = self._match_outreach_email(user_id, from_email_clean, in_reply_to, subject)

        if not outreach_email:
            return {"matched": False}

        lead = self.lead_repo.get_by_id(user_id, outreach_email.lead_id)
        if not lead:
            return {"matched": False}

        conversation = self._get_or_create_conversation(user_id, outreach_email, subject)
        from app.models.email_outreach import ConversationMessage

        msg = ConversationMessage(
            conversation_id=conversation.id,
            outreach_email_id=outreach_email.id,
            direction="inbound",
            from_email=from_email_clean,
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            external_message_id=message_id,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)

        now = datetime.now(UTC)
        self.repo.update_outreach_email(
            outreach_email,
            {"status": OutreachEmailStatus.replied, "replied_at": now},
        )

        for email in self.repo.list_outreach_emails(
            user_id, campaign_id=outreach_email.outreach_campaign_id, limit=500
        ):
            if email.lead_id == lead.id and email.status == OutreachEmailStatus.queued:
                self.repo.update_outreach_email(email, {"status": OutreachEmailStatus.cancelled})

        conversation.follow_ups_stopped = True
        conversation.status = ConversationStatus.responded
        conversation.last_message_at = now
        self.db.commit()

        intent, summary, draft_subject, draft_body = self._analyze_reply(
            user_id, body_text, conversation.id
        )
        conversation.reply_intent = intent
        conversation.reply_summary = summary
        self.db.commit()

        if intent == ReplyIntent.unsubscribe:
            self.lead_repo.update(lead, {"status": LeadStatus.lost})
            self.repo.add_timeline_event(
                {
                    "user_id": user_id,
                    "lead_id": lead.id,
                    "conversation_id": conversation.id,
                    "event_type": EmailTimelineEventType.unsubscribed,
                    "description": "Lead unsubscribed",
                }
            )
        elif intent == ReplyIntent.interested:
            self.lead_repo.update(lead, {"status": LeadStatus.interested})
        elif intent == ReplyIntent.meeting_request:
            self.lead_repo.update(lead, {"status": LeadStatus.follow_up})
        else:
            self.lead_repo.update(lead, {"status": LeadStatus.follow_up})

        self.repo.add_timeline_event(
            {
                "user_id": user_id,
                "lead_id": lead.id,
                "outreach_email_id": outreach_email.id,
                "conversation_id": conversation.id,
                "event_type": EmailTimelineEventType.replied,
                "description": f"Reply received: {summary}",
                "event_meta": {"intent": intent.value},
            }
        )

        settings = self.repo.get_or_create_settings(user_id)
        from app.models.email_outreach import AiReplyDraft

        draft_status = AiReplyDraftStatus.pending_approval
        auto_send = False
        if settings.auto_reply_enabled:
            if settings.auto_reply_simple_only:
                auto_send = intent in SAFE_AUTO_REPLY_INTENTS
            else:
                auto_send = intent not in SKIP_AUTO_REPLY_INTENTS

        if auto_send:
            draft_status = AiReplyDraftStatus.auto_sent

        draft = AiReplyDraft(
            user_id=user_id,
            conversation_id=conversation.id,
            inbound_message_id=msg.id,
            detected_intent=intent,
            summary=summary,
            draft_subject=draft_subject,
            draft_body=draft_body,
            status=draft_status,
        )
        self.db.add(draft)
        settings.ai_replies_generated += 1
        self.db.commit()

        NotificationService(self.db).notify(
            user_id,
            NotificationType.reply_received,
            f"Reply from {lead.company_name or from_email_clean}",
            summary,
            lead_id=lead.id,
        )

        self.repo.add_timeline_event(
            {
                "user_id": user_id,
                "lead_id": lead.id,
                "conversation_id": conversation.id,
                "event_type": EmailTimelineEventType.ai_draft_created,
                "description": "AI reply draft created",
            }
        )

        if auto_send:
            self.approve_draft(user_id, draft.id)

        return {
            "matched": True,
            "lead_id": lead.id,
            "conversation_id": conversation.id,
            "intent": intent.value,
            "draft_id": draft.id,
        }

    def _extract_email(self, raw: str) -> str:
        match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", raw)
        return match.group(0).lower() if match else raw.lower().strip()

    def _match_outreach_email(self, user_id: int, from_email: str, in_reply_to: str | None, subject: str):
        emails = self.repo.list_outreach_emails(user_id, limit=500)
        if in_reply_to:
            for e in emails:
                if e.external_message_id and e.external_message_id in in_reply_to:
                    return e
        for e in emails:
            if e.to_email.lower() == from_email:
                return e
        clean_subject = subject.lower().replace("re:", "").strip()
        for e in emails:
            if e.subject.lower().strip() in clean_subject or clean_subject in e.subject.lower():
                return e
        return None

    def _get_or_create_conversation(self, user_id, outreach_email, subject):
        conversations = self.repo.list_conversations(user_id, limit=200)
        for c in conversations:
            if c.lead_id == outreach_email.lead_id:
                return c
        return self.repo.create_conversation(
            {
                "user_id": user_id,
                "lead_id": outreach_email.lead_id,
                "outreach_campaign_id": outreach_email.outreach_campaign_id,
                "email_account_id": outreach_email.email_account_id,
                "subject": subject,
                "thread_id": outreach_email.thread_id,
            }
        )

    def _conversation_history(self, conversation_id: int) -> str:
        from app.models.email_outreach import ConversationMessage

        messages = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(20)
            .all()
        )
        if not messages:
            return "No prior messages"
        lines = []
        for m in messages:
            direction = "You" if m.direction == "outbound" else "Lead"
            lines.append(f"{direction}: {m.body_text[:300]}")
        return "\n".join(lines)

    def _analyze_reply(
        self, user_id: int, reply_text: str, conversation_id: int | None = None
    ) -> tuple[ReplyIntent, str, str, str]:
        history = (
            self._conversation_history(conversation_id) if conversation_id else "No prior messages"
        )
        groq = GroqService(self.db, user_id)
        try:
            raw = groq._chat(
                REPLY_ANALYSIS_PROMPT.format(
                    reply_text=reply_text[:2000],
                    conversation_history=history[:3000],
                ),
                max_tokens=350,
                temperature=0.3,
            )
            text = raw.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
                text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            intent_str = str(data.get("intent", "other"))
            try:
                intent = ReplyIntent(intent_str)
            except ValueError:
                intent = ReplyIntent.other
            return (
                intent,
                str(data.get("summary", "Reply received")),
                str(data.get("draft_subject", "Re: your message")),
                str(data.get("draft_body", "Thanks for your reply — I'll get back to you shortly.")),
            )
        except Exception:
            return (
                ReplyIntent.other,
                "Reply received",
                "Re: your message",
                "Thanks for getting back to me. Happy to share more details whenever works for you.",
            )

    def approve_draft(self, user_id: int, draft_id: int, *, edit_subject: str | None = None, edit_body: str | None = None) -> None:
        draft = self.repo.get_ai_draft(user_id, draft_id)
        if not draft:
            raise ValueError("Draft not found")

        if edit_subject:
            draft.draft_subject = edit_subject
        if edit_body:
            draft.draft_body = edit_body

        draft.status = AiReplyDraftStatus.approved
        self.db.commit()

        self.queue.enqueue(
            user_id,
            OutreachJobType.send_email,
            {
                "reply_draft_id": draft.id,
                "conversation_id": draft.conversation_id,
                "subject": draft.draft_subject,
                "body": draft.draft_body,
            },
            idempotency_key=f"reply_send_{draft.id}",
        )
