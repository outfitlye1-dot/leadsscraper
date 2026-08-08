"""Build email outreach chat threads (sent + received) for the Chat UI."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.email_outreach import (
    ConversationMessage,
    ConversationStatus,
    EmailConversation,
    OutreachEmail,
    OutreachEmailStatus,
)
from app.models.lead import Lead, LeadStatus
from app.models.user import User
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.repositories.lead_repository import LeadRepository
from app.services.email_outreach.sender_profile import build_sender_business_context
from app.services.email_outreach.transport import EmailTransportError, send_email
from app.services.groq_service import GroqService
from app.utils.chat_message_body import clean_chat_display_body, extract_subject_and_body
from app.utils.customer_language import language_rules_for_country
from app.utils.outreach_tone import build_pricing_rules_for_user, sanitize_paid_outreach_message
from app.utils.prompt_format import safe_prompt_format


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


CHAT_AI_REPLY_PROMPT = """You are a real human salesperson closing a deal by email/chat. Natural tone — not a bot.

YOUR BUSINESS FACTS (allowed ONLY — invent nothing else):
{business_context}

{pricing_rules}

{language_rules}

{deal_memory}

Lead: {lead_name} <{lead_email}>
Subject: {subject}

FULL THREAD HISTORY (continue this deal — remember prior offers/asks; never restart cold):
{history}

YOUR LAST OUTBOUND (DO NOT repeat this or say the same thing again):
{last_outbound}

LATEST CUSTOMER MESSAGE (answer this, then move the SAME deal forward):
{latest_customer_message}

Owner notes (optional): {hint}

HARD RULES:
1. Write in the LANGUAGE rules language (or match the customer if they already wrote). Sound human. Match their energy.
2. Use FULL history. Stay on the deal path already built.
3. NEVER send the same (or near-same) message twice.
4. PRICE TIMING:
   - No price/number unless they asked OR you already quoted in history.
   - First price ask → HIGH + short package line.
   - Already quoted → never reset to HIGH; continue toward mid/floor close.
5. PACKAGE AUTO-ADJUST:
   - "ok" → confirm last price + next step.
   - "less" / lower budget → lighter package/scope, counter toward mid (>= floor).
6. 1–3 sentences, under 55 words. No fluff.
7. Use only business facts + pricing + history.
8. Emoji: on roughly 1 in 3 replies, ONE friendly emoji. Otherwise none.

Return ONLY JSON:
{{
  "draft_subject": "email subject, keep Re: if continuing",
  "draft_body": "fresh human reply that advances the same deal from history"
}}
"""


SENT_STATUSES = {
    OutreachEmailStatus.sent,
    OutreachEmailStatus.delivered,
    OutreachEmailStatus.opened,
    OutreachEmailStatus.replied,
}

# Email can't give true presence — treat recent inbound activity as "online".
ONLINE_WINDOW_SECONDS = 15 * 60


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class EmailChatService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailOutreachRepository(db)
        self.lead_repo = LeadRepository(db)

    def list_threads(self, user: User, *, limit: int = 80) -> list[dict]:
        conversations = self.repo.list_conversations(user.id, limit=limit)
        by_lead: dict[int, dict] = {}

        lead_ids = [c.lead_id for c in conversations]
        leads = (
            self.db.query(Lead)
            .filter(Lead.user_id == user.id, Lead.id.in_(lead_ids))
            .all()
            if lead_ids
            else []
        )
        lead_map = {lead.id: lead for lead in leads}

        for conv in conversations:
            lead = lead_map.get(conv.lead_id)
            last_preview = self._last_preview_for_conversation(conv.id)
            by_lead[conv.lead_id] = {
                "lead_id": conv.lead_id,
                "conversation_id": conv.id,
                "lead_name": (lead.company_name if lead else None) or f"Lead #{conv.lead_id}",
                "lead_email": (lead.email if lead else None) or "",
                "subject": conv.subject,
                "status": conv.status.value if hasattr(conv.status, "value") else str(conv.status),
                "reply_intent": (
                    conv.reply_intent.value
                    if conv.reply_intent and hasattr(conv.reply_intent, "value")
                    else (str(conv.reply_intent) if conv.reply_intent else None)
                ),
                "reply_summary": conv.reply_summary,
                "last_message_at": _as_utc(conv.last_message_at or conv.created_at),
                "last_preview": last_preview,
                "has_reply": bool(conv.status == ConversationStatus.responded),
                "message_count": self._message_count_for_lead(user.id, conv.lead_id, conv.id),
                "unread_count": self._unread_count_for_conversation(conv),
                "is_manual_chat": self._is_manual_chat_lead(lead),
                **self._presence_fields(conv.id),
            }

        # Leads with sent emails but no conversation yet (so Chat still shows them)
        emailed_lead_ids = {
            row.lead_id
            for row in (
                self.db.query(OutreachEmail.lead_id)
                .filter(
                    OutreachEmail.user_id == user.id,
                    OutreachEmail.status.in_(list(SENT_STATUSES)),
                )
                .distinct()
                .all()
            )
        }
        missing = [lid for lid in emailed_lead_ids if lid not in by_lead]
        if missing:
            missing_leads = (
                self.db.query(Lead)
                .filter(Lead.user_id == user.id, Lead.id.in_(missing))
                .all()
            )
            for lead in missing_leads:
                latest = (
                    self.db.query(OutreachEmail)
                    .filter(
                        OutreachEmail.user_id == user.id,
                        OutreachEmail.lead_id == lead.id,
                        OutreachEmail.status.in_(list(SENT_STATUSES)),
                    )
                    .order_by(OutreachEmail.sent_at.desc().nullslast())
                    .first()
                )
                preview = (latest.body_text or "")[:160] if latest else None
                by_lead[lead.id] = {
                    "lead_id": lead.id,
                    "conversation_id": None,
                    "lead_name": lead.company_name or f"Lead #{lead.id}",
                    "lead_email": lead.email or (latest.to_email if latest else "") or "",
                    "subject": (latest.subject if latest else "Outreach"),
                    "status": "awaiting_reply",
                    "reply_intent": None,
                    "reply_summary": None,
                    "last_message_at": _as_utc(
                        (latest.sent_at if latest else None) or (latest.created_at if latest else None)
                    ),
                    "last_preview": preview,
                    "has_reply": False,
                    "message_count": self._message_count_for_lead(user.id, lead.id, None),
                    "unread_count": 0,
                    "is_manual_chat": self._is_manual_chat_lead(lead),
                    "is_online": False,
                    "last_seen_at": None,
                }

        threads = list(by_lead.values())
        threads.sort(
            key=lambda t: t["last_message_at"] or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return threads[:limit]

    def _last_preview_for_conversation(self, conversation_id: int) -> str | None:
        msg = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.received_at.desc())
            .first()
        )
        if msg and msg.body_text:
            return msg.body_text.strip()[:160]
        return None

    def _unread_count_for_conversation(self, conv: EmailConversation) -> int:
        """Inbound messages newer than last_read_at (or all inbound if never opened)."""
        q = self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conv.id,
            ConversationMessage.direction == "inbound",
        )
        last_read = _as_utc(conv.last_read_at)
        if last_read is not None:
            q = q.filter(ConversationMessage.received_at > last_read)
        return q.count()

    def _presence_fields(self, conversation_id: int | None) -> dict:
        """Approximate online/offline from last inbound activity."""
        if not conversation_id:
            return {"is_online": False, "last_seen_at": None}
        last_in = (
            self.db.query(ConversationMessage)
            .filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.direction == "inbound",
            )
            .order_by(ConversationMessage.received_at.desc())
            .first()
        )
        if not last_in:
            return {"is_online": False, "last_seen_at": None}
        last_seen = _as_utc(last_in.received_at)
        if not last_seen:
            return {"is_online": False, "last_seen_at": None}
        age = (datetime.now(UTC) - last_seen).total_seconds()
        return {"is_online": age <= ONLINE_WINDOW_SECONDS, "last_seen_at": last_seen}

    def _delivery_status_for_outbound(
        self,
        *,
        status: str | None,
        opened_at: datetime | None,
        delivered_at: datetime | None,
        sent_at: datetime | None,
        latest_inbound_at: datetime | None,
    ) -> str:
        """WhatsApp-style receipt: sent → delivered → read."""
        st = (status or "sent").lower()
        if opened_at or st in {"opened", "replied"}:
            return "read"
        if latest_inbound_at and sent_at and latest_inbound_at >= sent_at:
            # They replied after (or around) this message → treat as read
            return "read"
        if delivered_at or st == "delivered":
            return "delivered"
        return "sent"

    def _apply_delivery_receipts(self, bubbles: list[dict]) -> None:
        inbound_times = [
            b["sent_at"]
            for b in bubbles
            if b.get("direction") == "inbound" and b.get("sent_at")
        ]
        latest_inbound = max(inbound_times) if inbound_times else None
        for b in bubbles:
            if b.get("direction") != "outbound":
                b["delivery_status"] = None
                continue
            b["delivery_status"] = self._delivery_status_for_outbound(
                status=b.get("status"),
                opened_at=b.pop("opened_at", None),
                delivered_at=b.pop("delivered_at", None),
                sent_at=b.get("sent_at"),
                latest_inbound_at=latest_inbound,
            )

    def mark_thread_read(self, user: User, lead_id: int) -> None:
        conversation = (
            self.db.query(EmailConversation)
            .filter(
                EmailConversation.user_id == user.id,
                EmailConversation.lead_id == lead_id,
            )
            .order_by(EmailConversation.created_at.desc())
            .first()
        )
        if not conversation:
            return
        conversation.last_read_at = datetime.now(UTC)
        self.db.commit()

    def _message_count_for_lead(
        self,
        user_id: int,
        lead_id: int,
        conversation_id: int | None,
    ) -> int:
        email_ids = {
            row.id
            for row in (
                self.db.query(OutreachEmail.id)
                .filter(
                    OutreachEmail.user_id == user_id,
                    OutreachEmail.lead_id == lead_id,
                    OutreachEmail.status.in_(list(SENT_STATUSES)),
                )
                .all()
            )
        }
        count = len(email_ids)
        if not conversation_id:
            return count

        msgs = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .all()
        )
        for msg in msgs:
            if msg.direction == "inbound":
                count += 1
            elif not msg.outreach_email_id or msg.outreach_email_id not in email_ids:
                count += 1
        return count

    def _is_manual_chat_lead(self, lead: Lead | None) -> bool:
        return bool(lead and (lead.source or "").strip().lower() == "manual_chat")

    def get_messages(self, user: User, lead_id: int) -> dict:
        lead = self.lead_repo.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        conversation = (
            self.db.query(EmailConversation)
            .filter(
                EmailConversation.user_id == user.id,
                EmailConversation.lead_id == lead_id,
            )
            .order_by(EmailConversation.created_at.desc())
            .first()
        )

        bubbles: list[dict] = []
        seen_ext: set[str] = set()
        seen_email_ids: set[int] = set()

        emails = (
            self.db.query(OutreachEmail)
            .filter(
                OutreachEmail.user_id == user.id,
                OutreachEmail.lead_id == lead_id,
                OutreachEmail.status.in_(list(SENT_STATUSES)),
            )
            .order_by(OutreachEmail.sent_at.asc().nullslast(), OutreachEmail.created_at.asc())
            .all()
        )
        account_email = ""
        for email in emails:
            seen_email_ids.add(email.id)
            account = (
                self.repo.get_account(user.id, email.email_account_id)
                if email.email_account_id
                else None
            )
            from_addr = account.email_address if account else "you"
            account_email = account_email or from_addr
            ext = email.external_message_id or ""
            if ext:
                seen_ext.add(ext)
            embedded_subj, _ = extract_subject_and_body(email.body_text or "")
            display_subject = (email.subject or embedded_subj or "Outreach").strip()
            display_body = clean_chat_display_body(
                email.body_text, fallback_subject=email.subject
            )
            bubbles.append(
                {
                    "id": f"email-{email.id}",
                    "direction": "outbound",
                    "from_email": from_addr,
                    "to_email": email.to_email,
                    "subject": display_subject,
                    "body_text": display_body,
                    "sent_at": _as_utc(email.sent_at or email.created_at),
                    "status": email.status.value if hasattr(email.status, "value") else str(email.status),
                    "source": "outreach_email",
                    "outreach_email_id": email.id,
                    "opened_at": _as_utc(email.opened_at),
                    "delivered_at": _as_utc(email.delivered_at),
                }
            )

        if conversation:
            msgs = (
                self.db.query(ConversationMessage)
                .filter(ConversationMessage.conversation_id == conversation.id)
                .order_by(ConversationMessage.received_at.asc())
                .all()
            )
            for msg in msgs:
                # Skip outbound message that mirrors an outreach email already shown
                if (
                    msg.direction == "outbound"
                    and msg.outreach_email_id
                    and msg.outreach_email_id in seen_email_ids
                ):
                    continue
                if msg.external_message_id and msg.external_message_id in seen_ext:
                    continue
                if msg.external_message_id:
                    seen_ext.add(msg.external_message_id)
                embedded_subj, _ = extract_subject_and_body(msg.body_text or "")
                display_subject = (msg.subject or embedded_subj or "Chat").strip()
                display_body = clean_chat_display_body(
                    msg.body_text, fallback_subject=msg.subject
                )
                bubbles.append(
                    {
                        "id": f"msg-{msg.id}",
                        "direction": msg.direction,
                        "from_email": msg.from_email,
                        "to_email": msg.to_email,
                        "subject": display_subject,
                        "body_text": display_body,
                        "sent_at": _as_utc(msg.received_at),
                        "status": "sent" if msg.direction == "outbound" else None,
                        "source": "conversation_message",
                        "outreach_email_id": msg.outreach_email_id,
                        "opened_at": None,
                        "delivered_at": None,
                    }
                )

        bubbles.sort(key=lambda b: b["sent_at"] or datetime.min.replace(tzinfo=UTC))
        self._apply_delivery_receipts(bubbles)

        if conversation:
            # Avoid committing on every 2–5s UI poll — only refresh read cursor periodically
            last_read = _as_utc(conversation.last_read_at)
            now = datetime.now(UTC)
            if last_read is None or (now - last_read).total_seconds() > 30:
                conversation.last_read_at = now
                self.db.commit()

        presence = self._presence_fields(conversation.id if conversation else None)

        return {
            "lead_id": lead.id,
            "conversation_id": conversation.id if conversation else None,
            "lead_name": lead.company_name,
            "lead_email": lead.email or "",
            "subject": (conversation.subject if conversation else (bubbles[0]["subject"] if bubbles else "Chat")),
            "status": (
                (conversation.status.value if hasattr(conversation.status, "value") else str(conversation.status))
                if conversation
                else ("awaiting_reply" if bubbles else "empty")
            ),
            "messages": bubbles,
            "is_online": presence["is_online"],
            "last_seen_at": presence["last_seen_at"],
        }

    def generate_ai_reply(
        self,
        user: User,
        lead_id: int,
        *,
        hint: str | None = None,
    ) -> dict[str, str]:
        detail = self.get_messages(user, lead_id)
        messages = detail.get("messages") or []
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No messages yet — send outreach first so AI has context",
            )

        from app.services.email_outreach.reply import (
            ReplyService,
            _clean_customer_text,
            _is_near_duplicate,
            _is_vague_filler,
        )

        lines: list[str] = []
        latest_customer = ""
        last_outbound = "(none yet)"
        for m in messages[-40:]:
            body = (m.get("body_text") or "")[:500]
            if m.get("direction") == "outbound":
                # Skip past filler so the model does not copy it
                if _is_vague_filler(body):
                    continue
                lines.append(f"You: {body}")
                if body.strip():
                    last_outbound = body.strip()[:500]
            else:
                lines.append(f"Lead: {body}")
                if body.strip():
                    latest_customer = body.strip()
        history = "\n".join(lines) if lines else "No prior messages"
        if not latest_customer:
            last = messages[-1] if messages else {}
            latest_customer = (last.get("body_text") or "").strip()[:500] or "(no customer message yet)"

        # Prefer only the customer's new text (drop quoted history)
        latest_customer = _clean_customer_text(latest_customer) or latest_customer

        subject = detail.get("subject") or "Re: Outreach"
        if not str(subject).lower().startswith("re:"):
            subject = f"Re: {subject}"

        deal_memory = ReplyService(self.db)._deal_memory(user.id, history, latest_customer)
        business_context = build_sender_business_context(
            self.db, user.id, for_replies=True
        )
        pricing_rules = build_pricing_rules_for_user(self.db, user.id)
        lead = self.lead_repo.get_by_id(user.id, lead_id)
        language_rules = language_rules_for_country(
            lead.country if lead else None,
            lead.city if lead else None,
            channel="email",
        )
        groq = GroqService(self.db, user.id)
        prompt = safe_prompt_format(
            CHAT_AI_REPLY_PROMPT,
            business_context=business_context[:2800],
            lead_name=detail.get("lead_name") or f"Lead #{lead_id}",
            lead_email=detail.get("lead_email") or "",
            subject=subject,
            history=history[:3600],
            last_outbound=last_outbound,
            latest_customer_message=latest_customer[:1200],
            hint=(hint or "").strip()[:500] or "(none)",
            pricing_rules=pricing_rules,
            language_rules=language_rules,
            deal_memory=deal_memory,
        )
        try:
            raw = groq._chat(prompt, max_tokens=220, temperature=0.45)
            text = (raw or "").strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
                text = re.sub(r"\s*```$", "", text)
            data = None
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]*\}", text)
                if match:
                    data = json.loads(match.group(0))
            if not isinstance(data, dict):
                raise ValueError("AI did not return JSON")
            draft_subject = str(data.get("draft_subject") or subject).strip()
            draft_body = sanitize_paid_outreach_message(
                str(data.get("draft_body") or "").strip()
            )
            if not draft_body or _is_vague_filler(draft_body):
                raise ValueError("empty or vague AI body")
            if last_outbound != "(none yet)" and _is_near_duplicate(draft_body, last_outbound):
                # One retry with a harder "no repeat + close the deal" nudge
                retry = safe_prompt_format(
                    CHAT_AI_REPLY_PROMPT,
                    business_context=business_context[:2800],
                    lead_name=detail.get("lead_name") or f"Lead #{lead_id}",
                    lead_email=detail.get("lead_email") or "",
                    subject=subject,
                    history=history[:3600],
                    last_outbound=last_outbound,
                    latest_customer_message=latest_customer[:1200],
                    hint=(
                        f"{(hint or '').strip()} — IMPORTANT: write a NEW reply. "
                        "Do not repeat your last message. Continue same deal from history."
                    )[:500],
                    pricing_rules=pricing_rules,
                    language_rules=language_rules,
                    deal_memory=deal_memory,
                )
                raw2 = groq._chat(retry, max_tokens=220, temperature=0.55)
                text2 = (raw2 or "").strip()
                if text2.startswith("```"):
                    text2 = re.sub(r"^```(?:json)?\s*", "", text2, flags=re.IGNORECASE)
                    text2 = re.sub(r"\s*```$", "", text2)
                try:
                    data2 = json.loads(text2)
                except json.JSONDecodeError:
                    match2 = re.search(r"\{[\s\S]*\}", text2)
                    data2 = json.loads(match2.group(0)) if match2 else {}
                if isinstance(data2, dict):
                    alt = sanitize_paid_outreach_message(
                        str(data2.get("draft_body") or "").strip()
                    )
                    if alt and not _is_vague_filler(alt) and not _is_near_duplicate(alt, last_outbound):
                        draft_body = alt
                        if data2.get("draft_subject"):
                            draft_subject = str(data2["draft_subject"]).strip()
            if len(draft_body) > 320:
                draft_body = draft_body[:317].rsplit(" ", 1)[0] + "..."
            return {"subject": draft_subject[:500], "body": draft_body[:20000]}
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI reply generation failed: {exc}",
            ) from exc

    def send_ai_reply(
        self,
        user: User,
        lead_id: int,
        *,
        hint: str | None = None,
        account_id: int | None = None,
    ) -> dict:
        draft = self.generate_ai_reply(user, lead_id, hint=hint)
        return self.send_reply(
            user,
            lead_id,
            subject=draft["subject"],
            body=draft["body"],
            account_id=account_id,
        )

    def _resolve_account(self, user: User, account_id: int | None):
        if account_id is not None:
            account = self.repo.get_account(user.id, account_id)
            if not account:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email account not found",
                )
            return account
        account = self.repo.get_default_account(user.id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connect an email account first (Email Outreach → Accounts)",
            )
        return account

    def start_manual_chat(
        self,
        user: User,
        *,
        email: str,
        name: str | None,
        subject: str,
        body: str,
        account_id: int | None = None,
    ) -> dict:
        to_email = (email or "").strip().lower()
        if not _EMAIL_RE.match(to_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a valid email address",
            )

        account = self._resolve_account(user, account_id)
        display_name = (name or "").strip() or to_email.split("@")[0]

        lead = (
            self.db.query(Lead)
            .filter(Lead.user_id == user.id, Lead.email.isnot(None))
            .filter(Lead.email == to_email)
            .first()
        )
        if not lead:
            # case-insensitive match
            leads = (
                self.db.query(Lead)
                .filter(Lead.user_id == user.id, Lead.email.isnot(None))
                .all()
            )
            lead = next(
                (L for L in leads if (L.email or "").strip().lower() == to_email),
                None,
            )

        if not lead:
            lead = self.lead_repo.create(
                user.id,
                {
                    "company_name": display_name,
                    "contact_name": display_name,
                    "email": to_email,
                    "source": "manual_chat",
                    "status": LeadStatus.contacted,
                    "notes": "Added from Email Chat (manual)",
                },
            )
        else:
            updates: dict = {}
            if name and name.strip() and (
                not lead.company_name or lead.company_name == (lead.email or "").split("@")[0]
            ):
                updates["company_name"] = name.strip()
            if not lead.email:
                updates["email"] = to_email
            if updates:
                for k, v in updates.items():
                    setattr(lead, k, v)
                self.db.commit()
                self.db.refresh(lead)

        sent = self.send_reply(
            user,
            lead.id,
            subject=subject.strip() or "Hello",
            body=body.strip(),
            account_id=account.id,
        )
        detail = self.get_messages(user, lead.id)
        detail["last_sent"] = sent
        return detail

    def send_reply(
        self,
        user: User,
        lead_id: int,
        *,
        subject: str,
        body: str,
        account_id: int | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> dict:
        lead = self.lead_repo.get_by_id(user.id, lead_id)
        if not lead or not lead.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead has no email address",
            )

        attachments = attachments or []
        body_clean = (body or "").strip()
        if not body_clean and not attachments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Write a message or attach a file",
            )

        account = self._resolve_account(user, account_id)

        conversation = (
            self.db.query(EmailConversation)
            .filter(
                EmailConversation.user_id == user.id,
                EmailConversation.lead_id == lead_id,
            )
            .order_by(EmailConversation.created_at.desc())
            .first()
        )
        if not conversation:
            latest = (
                self.db.query(OutreachEmail)
                .filter(
                    OutreachEmail.user_id == user.id,
                    OutreachEmail.lead_id == lead_id,
                )
                .order_by(OutreachEmail.created_at.desc())
                .first()
            )
            conversation = EmailConversation(
                user_id=user.id,
                lead_id=lead_id,
                email_account_id=account.id,
                outreach_campaign_id=latest.outreach_campaign_id if latest else None,
                subject=subject.strip() or (latest.subject if latest else "Chat"),
                thread_id=latest.thread_id if latest else None,
                status=ConversationStatus.active,
                last_message_at=datetime.now(UTC),
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
        else:
            conversation.email_account_id = account.id

        # Persist human-readable attachment labels in chat history
        store_body = body_clean
        if attachments:
            labels = []
            for name, _data, ctype in attachments:
                if (ctype or "").startswith("audio/"):
                    labels.append(f"🎤 {name}")
                elif (ctype or "").startswith("image/"):
                    labels.append(f"🖼️ {name}")
                else:
                    labels.append(f"📎 {name}")
            store_body = (store_body + "\n\n" if store_body else "") + "\n".join(labels)

        try:
            message_id = send_email(
                account,
                lead.email,
                subject.strip(),
                body_clean or "(attachment)",
                attachments=attachments or None,
            )
        except EmailTransportError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        now = datetime.now(UTC)
        msg = ConversationMessage(
            conversation_id=conversation.id,
            direction="outbound",
            from_email=account.email_address,
            to_email=lead.email,
            subject=subject.strip(),
            body_text=store_body or "(attachment)",
            external_message_id=message_id,
            received_at=now,
        )
        self.db.add(msg)
        conversation.last_message_at = now
        conversation.status = ConversationStatus.active
        conversation.subject = conversation.subject or subject.strip()
        self.db.commit()
        self.db.refresh(msg)

        return {
            "id": f"msg-{msg.id}",
            "direction": "outbound",
            "from_email": msg.from_email,
            "to_email": msg.to_email,
            "subject": msg.subject,
            "body_text": msg.body_text,
            "sent_at": _as_utc(msg.received_at),
            "status": "sent",
            "source": "conversation_message",
            "outreach_email_id": None,
            "delivery_status": "sent",
        }

    def delete_thread(self, user: User, lead_id: int, *, delete_lead: bool = False) -> None:
        from app.models.email_outreach import AiReplyDraft, EmailTimelineEvent

        lead = self.lead_repo.get_by_id(user.id, lead_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        conv_ids = [
            cid
            for (cid,) in (
                self.db.query(EmailConversation.id)
                .filter(
                    EmailConversation.user_id == user.id,
                    EmailConversation.lead_id == lead_id,
                )
                .all()
            )
        ]

        try:
            if conv_ids:
                # Drafts reference conversations/messages — must go first (SQLite often lacks CASCADE)
                self.db.query(AiReplyDraft).filter(
                    AiReplyDraft.conversation_id.in_(conv_ids)
                ).delete(synchronize_session=False)

                self.db.query(ConversationMessage).filter(
                    ConversationMessage.conversation_id.in_(conv_ids)
                ).delete(synchronize_session=False)

            self.db.query(EmailTimelineEvent).filter(
                EmailTimelineEvent.user_id == user.id,
                EmailTimelineEvent.lead_id == lead_id,
            ).delete(synchronize_session=False)

            self.db.query(EmailConversation).filter(
                EmailConversation.user_id == user.id,
                EmailConversation.lead_id == lead_id,
            ).delete(synchronize_session=False)

            self.db.query(OutreachEmail).filter(
                OutreachEmail.user_id == user.id,
                OutreachEmail.lead_id == lead_id,
            ).delete(synchronize_session=False)

            if delete_lead:
                # Explicit contact delete from Chat — always allowed, even if saved
                self.db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == user.id).update(
                    {"is_saved": False, "saved_at": None},
                    synchronize_session=False,
                )
                self.db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == user.id).delete(
                    synchronize_session=False
                )

            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete chat: {exc}",
            ) from exc
