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
from app.services.email_outreach.sender_profile import build_sender_business_context
from app.utils.customer_language import language_rules_for_country
from app.utils.outreach_tone import (
    build_pricing_rules_for_user,
    resolve_pricing_from_brain,
    sanitize_paid_outreach_message,
)
from app.utils.prompt_format import safe_prompt_format
from app.repositories.brain_repository import BrainRepository


REPLY_ANALYSIS_PROMPT = """You are a real human salesperson closing a deal over email/chat. Natural tone — like texting a client, not a bot.

YOUR BUSINESS FACTS (invent nothing outside this):
{business_context}

{pricing_rules}

{language_rules}

{deal_memory}

FULL THREAD HISTORY (use this — remember what you both already said; never restart the deal cold):
{conversation_history}

YOUR LAST OUTBOUND (DO NOT repeat this or say the same thing again):
{last_outbound}

CUSTOMER'S LATEST MESSAGE:
{reply_text}

HARD RULES:
1. Write in the LANGUAGE rules language (or match the customer's language if they already wrote). Sound human. Match their energy.
2. Read the FULL history first. Continue the SAME deal path.
3. Answer what they just said — then MOVE the deal forward.
4. NEVER send the same (or near-same) message twice.
5. PRICE TIMING:
   - If they have NOT asked about price/cost/package yet → do NOT quote a number. Talk about the work / next step.
   - If they ask price (or kitna / fees / package / budget) AND you have not quoted yet → open at HIGH with one short package line.
   - If you already quoted → never reset to HIGH.
6. PACKAGE AUTO-ADJUST:
   - "ok" / "sounds good" / "let's do it" → confirm last quoted price and ask a simple next step.
   - "less" / "too expensive" / lower number → shrink scope (lighter package) and counter toward mid, still >= floor. One clear sentence on what changes.
7. Keep it short: 1–3 sentences, under 55 words. No corporate fluff.
8. Use only business facts + pricing + history. Missing detail → one clear question — don't invent.
9. Emoji: on roughly 1 in 3 replies, add ONE friendly emoji (😊 🙂 👍 ✨ 🙏 😄). Other replies: no emoji.

Return ONLY JSON:
{{
  "intent": "interested|not_interested|question|meeting_request|unsubscribe|out_of_office|other",
  "summary": "what they said in under 12 words",
  "draft_subject": "Re: your message",
  "draft_body": "fresh human reply that advances the same deal from history"
}}
"""

SIMPLE_REPLY_PROMPT = """FULL THREAD HISTORY:
{conversation_history}

{deal_memory}

{language_rules}

Customer just said:
{reply_text}

Your last reply (do NOT repeat):
{last_outbound}

Facts:
{business_context}

{pricing_rules}

Write a NEW short human reply (max 50 words) in the LANGUAGE rules language (or match the customer).
- No price unless they asked or you already quoted in history.
- If they ask price and none quoted yet → HIGH + short package line.
- If they say less → adjust package/scope toward mid (>= floor).
- If they say ok → confirm and lock next step.
- Sound human. Never repeat your last reply. Sometimes (not always) one light emoji.

Return ONLY JSON:
{{"intent":"question","summary":"short","draft_subject":"Re: your message","draft_body":"new human deal-moving answer"}}
"""

_VAGUE_FILLER_RE = re.compile(
    r"("
    r"happy to share more details|"
    r"whenever works for you|"
    r"get back to you shortly|"
    r"i'?ll get back to you|"
    r"thanks for getting back to me|"
    r"let me know if you(?:'d| would) like|"
    r"feel free to (?:reach|contact)|"
    r"looking forward to hearing"
    r")",
    re.I,
)


def _is_vague_filler(text: str | None) -> bool:
    if not text or not text.strip():
        return True
    body = text.strip()
    if len(body) < 12:
        return True
    lowered = body.lower()
    if lowered in _GENERIC_FALLBACK_BODIES:
        return True
    if _VAGUE_FILLER_RE.search(body):
        return True
    # No substance: thanks + empty promise
    if "thank" in lowered and ("share" in lowered or "get back" in lowered or "details" in lowered):
        if not any(ch.isdigit() for ch in body) and len(body) < 120:
            return True
    return False


# Exact known fillers (normalized)
_GENERIC_FALLBACK_BODIES = {
    "thanks for getting back to me. happy to share more details whenever works for you.",
    "thanks for your reply — i'll get back to you shortly.",
    "thanks for your reply - i'll get back to you shortly.",
    "thanks for your reply — i'll get back to you shortly.",
}


def _clean_customer_text(raw: str | None) -> str:
    """Keep only the new customer text — drop quoted email history."""
    if not raw:
        return ""
    text = raw.replace("\r\n", "\n").replace("\u202f", " ").strip()
    cut_patterns = [
        r"\nOn\s+[^\n]+wrote:\s*\n",
        r"\nOn\s+[^\n]+<[^>]+>\s*wrote:\s*\n",
        r"\n-{2,}\s*Original Message\s*-{2,}",
        r"\nFrom:\s*[^\n]+\nSent:\s*[^\n]+",
        r"\n_{5,}\n",
        r"\nBegin forwarded message:\s*\n",
    ]
    for pattern in cut_patterns:
        idx = re.search(pattern, text, flags=re.I)
        if idx and idx.start() > 0:
            text = text[: idx.start()]
            break
    lines = [ln for ln in text.split("\n") if not re.match(r"^\s*>", ln)]
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:1500]


def _normalize_for_compare(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s$]", "", t)
    return t


def _is_near_duplicate(a: str | None, b: str | None) -> bool:
    """True if two messages are basically the same reply."""
    na = _normalize_for_compare(a or "")
    nb = _normalize_for_compare(b or "")
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) > 20 and (na in nb or nb in na):
        return True
    # token overlap
    ta = set(na.split())
    tb = set(nb.split())
    if not ta or not tb:
        return False
    overlap = len(ta & tb) / max(len(ta), len(tb))
    return overlap >= 0.82


SAFE_AUTO_REPLY_INTENTS = {ReplyIntent.question, ReplyIntent.out_of_office}
SKIP_AUTO_REPLY_INTENTS = {ReplyIntent.unsubscribe, ReplyIntent.not_interested}



def _parse_llm_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty LLM response")
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("no JSON object in LLM response")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not an object")
    return data



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
        skip_ai: bool = False,
    ) -> dict:
        from app.models.email_outreach import ConversationMessage, EmailConversation

        from_email_clean = self._extract_email(from_email)

        # Skip duplicates already stored in chat
        if message_id:
            existing = (
                self.db.query(ConversationMessage)
                .filter(ConversationMessage.external_message_id == message_id)
                .first()
            )
            if existing:
                return {"matched": True, "duplicate": True, "conversation_id": existing.conversation_id}

        outreach_email = self._match_outreach_email(user_id, from_email_clean, in_reply_to, subject)
        lead = None
        conversation = None

        if outreach_email:
            lead = self.lead_repo.get_by_id(user_id, outreach_email.lead_id)
            if lead:
                conversation = self._get_or_create_conversation(user_id, outreach_email, subject)
        else:
            chat_match = self._match_chat_context(
                user_id, from_email_clean, in_reply_to=in_reply_to, subject=subject
            )
            if chat_match:
                lead, conversation = chat_match

        if not lead or not conversation:
            return {"matched": False}

        msg = ConversationMessage(
            conversation_id=conversation.id,
            outreach_email_id=outreach_email.id if outreach_email else None,
            direction="inbound",
            from_email=from_email_clean,
            to_email=to_email,
            subject=subject or conversation.subject or "Re: Chat",
            body_text=body_text or "",
            external_message_id=message_id,
            received_at=datetime.now(UTC),
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)

        now = datetime.now(UTC)
        if outreach_email:
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

        try:
            if skip_ai:
                # Chat inbox poll must stay fast — don't block on Groq from the HTTP path
                intent, summary, draft_subject, draft_body, ai_ok = (
                    ReplyIntent.question,
                    "New reply",
                    f"Re: {subject}" if subject else "Re: your message",
                    self._contextual_fallback_body(user_id, body_text),
                    False,
                )
            else:
                intent, summary, draft_subject, draft_body, ai_ok = self._analyze_reply(
                    user_id, body_text, conversation.id
                )
        except Exception:
            intent, summary, draft_subject, draft_body, ai_ok = (
                ReplyIntent.other,
                "Reply received",
                f"Re: {subject}" if subject else "Re: your message",
                self._contextual_fallback_body(user_id, body_text),
                False,
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
                "outreach_email_id": outreach_email.id if outreach_email else None,
                "conversation_id": conversation.id,
                "event_type": EmailTimelineEventType.replied,
                "description": f"Reply received: {summary}",
                "event_meta": {"intent": intent.value},
            }
        )

        settings = self.repo.get_or_create_settings(user_id)
        from app.models.email_outreach import AiReplyDraft, ConversationMessage

        # Never auto-send a repeat of our last outbound
        last_out = (
            self.db.query(ConversationMessage)
            .filter(
                ConversationMessage.conversation_id == conversation.id,
                ConversationMessage.direction == "outbound",
            )
            .order_by(ConversationMessage.received_at.desc())
            .first()
        )
        if last_out and _is_near_duplicate(draft_body, last_out.body_text):
            # Force a fresh negotiation-style line instead of repeating
            draft_body = self._contextual_fallback_body(
                user_id, body_text, last_outbound=last_out.body_text or ""
            )
            if _is_near_duplicate(draft_body, last_out.body_text):
                draft_body = self._deal_nudge_body(user_id, body_text)

        draft_status = AiReplyDraftStatus.pending_approval
        auto_send = False
        if settings.auto_reply_enabled and not _is_vague_filler(draft_body):
            if settings.auto_reply_simple_only:
                auto_send = intent in SAFE_AUTO_REPLY_INTENTS
            else:
                auto_send = intent not in SKIP_AUTO_REPLY_INTENTS
            if not ai_ok and intent not in SAFE_AUTO_REPLY_INTENTS:
                auto_send = False
            if last_out and _is_near_duplicate(draft_body, last_out.body_text):
                auto_send = False

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

    def _match_chat_context(
        self,
        user_id: int,
        from_email: str,
        *,
        in_reply_to: str | None,
        subject: str,
    ):
        """Match inbound mail to a manual/chat conversation (no outreach_email row)."""
        from app.models.email_outreach import ConversationMessage, EmailConversation
        from app.models.lead import Lead

        # 1) Match by In-Reply-To → our outbound chat Message-ID
        if in_reply_to:
            outbound = (
                self.db.query(ConversationMessage)
                .join(EmailConversation, EmailConversation.id == ConversationMessage.conversation_id)
                .filter(
                    EmailConversation.user_id == user_id,
                    ConversationMessage.direction == "outbound",
                    ConversationMessage.external_message_id.isnot(None),
                )
                .order_by(ConversationMessage.received_at.desc())
                .limit(200)
                .all()
            )
            for m in outbound:
                ext = (m.external_message_id or "").strip()
                if ext and ext in in_reply_to:
                    conv = self.db.query(EmailConversation).filter(EmailConversation.id == m.conversation_id).first()
                    if conv:
                        lead = self.lead_repo.get_by_id(user_id, conv.lead_id)
                        if lead:
                            return lead, conv

        # 2) Match lead by sender email
        leads = (
            self.db.query(Lead)
            .filter(Lead.user_id == user_id, Lead.email.isnot(None))
            .all()
        )
        lead = next(
            (L for L in leads if (L.email or "").strip().lower() == from_email),
            None,
        )
        if not lead:
            return None

        conversation = (
            self.db.query(EmailConversation)
            .filter(
                EmailConversation.user_id == user_id,
                EmailConversation.lead_id == lead.id,
            )
            .order_by(EmailConversation.created_at.desc())
            .first()
        )
        if conversation:
            return lead, conversation

        # New conversation for this lead (e.g. they replied but we only had outbound chat)
        account = self.repo.get_default_account(user_id)
        conversation = self.repo.create_conversation(
            {
                "user_id": user_id,
                "lead_id": lead.id,
                "email_account_id": account.id if account else None,
                "subject": subject or f"Re: chat with {lead.company_name}",
                "status": ConversationStatus.responded,
                "last_message_at": datetime.now(UTC),
            }
        )
        return lead, conversation

    def _extract_email(self, raw: str) -> str:
        match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", raw)
        return match.group(0).lower() if match else raw.lower().strip()

    def _match_outreach_email(self, user_id: int, from_email: str, in_reply_to: str | None, subject: str):
        emails = self.repo.list_outreach_emails(user_id, limit=500)
        if in_reply_to:
            for e in emails:
                if e.external_message_id and e.external_message_id in in_reply_to:
                    return e
        # Prefer exact recipient match (who we emailed)
        for e in emails:
            if (e.to_email or "").lower() == from_email:
                return e
        # Subject match only if specific enough (avoid matching spam to "Hello")
        clean_subject = re.sub(r"^(re|fwd|fw)\s*:\s*", "", (subject or "").lower()).strip()
        if len(clean_subject) >= 8:
            for e in emails:
                e_subj = re.sub(r"^(re|fwd|fw)\s*:\s*", "", (e.subject or "").lower()).strip()
                if e_subj and (e_subj == clean_subject or e_subj in clean_subject or clean_subject in e_subj):
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
            .order_by(ConversationMessage.received_at.asc())
            .all()
        )
        # Keep the recent tail so long threads still fit the prompt
        if len(messages) > 40:
            messages = messages[-40:]
        if not messages:
            return "No prior messages"
        lines = []
        for m in messages:
            raw = m.body_text or ""
            body = _clean_customer_text(raw) if m.direction == "inbound" else raw.strip()
            body = body[:400]
            if not body:
                continue
            # Don't feed the model its own past filler — it copies those lines
            if m.direction == "outbound" and _is_vague_filler(body):
                continue
            direction = "You" if m.direction == "outbound" else "Lead"
            lines.append(f"{direction}: {body}")
        return "\n".join(lines) if lines else "No prior messages"

    def _deal_memory(self, user_id: int, history: str, reply_text: str = "") -> str:
        """Summarize negotiated numbers so AI continues the same deal path."""
        brain = BrainRepository(self.db).get_by_user(user_id)
        high, floor, currency = resolve_pricing_from_brain(brain)
        our_nums: list[float] = []
        their_nums: list[float] = []
        for line in (history or "").splitlines():
            low = line.strip()
            if low.startswith("You:"):
                n = self._extract_customer_number(low)
                if n is not None and floor <= n <= high * 1.2:
                    our_nums.append(n)
            elif low.startswith("Lead:"):
                n = self._extract_customer_number(low)
                if n is not None and 10 <= n <= high * 1.5:
                    their_nums.append(n)
        latest_their = self._extract_customer_number(_clean_customer_text(reply_text).lower())
        if latest_their is not None:
            their_nums.append(latest_their)

        last_our = our_nums[-1] if our_nums else None
        last_their = their_nums[-1] if their_nums else None
        bits = [
            "DEAL MEMORY (from this thread — OBEY):",
            "- Continue the SAME conversation/deal. Do not restart the pitch as if new.",
        ]
        if last_our is not None:
            bits.append(
                f"- You already quoted about {currency} {last_our:g}. "
                f"Do NOT reset to HIGH ({currency} {high:g}). "
                f"Next offer must stay <= {last_our:g} and >= floor {currency} {floor:g}."
            )
        else:
            bits.append(
                f"- No price quoted yet by you — first ask may open at HIGH {currency} {high:g}."
            )
        if last_their is not None:
            bits.append(
                f"- Customer last mentioned about {currency} {last_their:g} — respond to that number."
            )
        bits.append(
            "- Push the next close step (confirm scope / lock price / start work), not a fresh sales speech."
        )
        return "\n".join(bits)

    def _last_outbound_text(self, conversation_id: int | None) -> str:
        from app.models.email_outreach import ConversationMessage

        if not conversation_id:
            return "(none yet)"
        last = (
            self.db.query(ConversationMessage)
            .filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.direction == "outbound",
            )
            .order_by(ConversationMessage.received_at.desc())
            .first()
        )
        if not last or not (last.body_text or "").strip():
            return "(none yet)"
        return (last.body_text or "").strip()[:500]

    def _extract_customer_number(self, text: str) -> float | None:
        clean = text.replace(",", "")
        matches = re.findall(
            r"(?:\$|usd|pkr|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(k|thousand)?",
            clean,
            re.I,
        )
        nums: list[float] = []
        for raw, suffix in matches:
            try:
                val = float(raw)
            except ValueError:
                continue
            if suffix and suffix.lower() in {"k", "thousand"}:
                val *= 1000
            if 10 <= val <= 10_000_000:
                nums.append(val)
        return nums[-1] if nums else None

    def _deal_nudge_body(self, user_id: int, reply_text: str) -> str:
        brain = BrainRepository(self.db).get_by_user(user_id)
        high, floor, currency = resolve_pricing_from_brain(brain)
        mid = (high + floor) / 2
        offered = self._extract_customer_number(_clean_customer_text(reply_text).lower())
        if offered is not None:
            if offered >= floor:
                deal = min(max(offered, floor), high)
                return (
                    f"Alright — I can do this at {currency} {deal:g}. "
                    "Want me to lock that in and get started?"
                )
            return (
                f"I get it. For {currency} {floor:g} I can do a lighter package "
                "(simpler scope) so it still looks solid. Want to go with that?"
            )
        return (
            f"I can trim it to a lighter package around {currency} {mid:g} "
            "if we keep the scope simple. Does that work?"
        )

    def _contextual_fallback_body(
        self,
        user_id: int,
        reply_text: str,
        *,
        last_outbound: str = "",
    ) -> str:
        brain = BrainRepository(self.db).get_by_user(user_id)
        high, floor, currency = resolve_pricing_from_brain(brain)
        mid = (high + floor) / 2
        text = _clean_customer_text(reply_text).lower()
        services: list[str] = []
        if brain and brain.services:
            services = [str(s).strip() for s in brain.services if str(s).strip()][:4]

        offered = self._extract_customer_number(text)
        pushes_back = any(
            k in text
            for k in (
                "too high", "expensive", "lower", "discount", "can you do",
                "negotiate", "budget", "zyada", "kam", "sasta",
            )
        )
        asks_price = any(
            k in text
            for k in (
                "price", "pricing", "cost", "rate", "how much", "kitna",
                "qeemat", "charges", "quote", "package", "fee", "$", "pkr", "usd",
            )
        )
        asks_services = any(
            k in text
            for k in ("service", "what do you", "kya kart", "offer", "provide", "website", "kaam")
        )
        already_quoted_high = bool(
            last_outbound
            and (
                f"{high:g}" in last_outbound.replace(",", "")
                or str(int(high)) in last_outbound.replace(",", "")
            )
        )
        accepts = any(
            k in text
            for k in (
                "ok", "okay", "sounds good", "deal", "let's do", "lets do",
                "fine", "haan", "han", "theek", "go ahead",
            )
        )

        if offered is not None:
            body = self._deal_nudge_body(user_id, reply_text)
        elif accepts and (already_quoted_high or asks_price):
            # They agreed after a quote — lock without restarting the pitch
            lock = high if already_quoted_high else mid
            body = (
                f"Perfect — let's lock it at {currency} {lock:g}. "
                "Send me your details and I'll get started."
            )
        elif pushes_back:
            body = self._deal_nudge_body(user_id, reply_text)
        elif asks_price and not already_quoted_high:
            body = (
                f"Sure — a solid package for this is about {currency} {high:g}. "
                "That covers the full scope. Want me to walk you through what's included?"
            )
        elif asks_price:
            body = (
                f"I can do a lighter package around {currency} {mid:g} "
                f"if we keep it simple (lowest is {currency} {floor:g}). "
                "What budget were you thinking?"
            )
        elif asks_services and services:
            body = f"I mainly help with {', '.join(services)}. What do you need help with?"
        elif asks_services:
            body = "I help local businesses with websites and online presence. What are you looking for?"
        elif services:
            body = f"I mainly do {services[0]}. Happy to chat about what would help your business."
        else:
            body = "Happy to help — what do you need most right now?"

        if last_outbound and _is_near_duplicate(body, last_outbound):
            return self._deal_nudge_body(user_id, reply_text)
        return body

    def _analyze_reply(
        self, user_id: int, reply_text: str, conversation_id: int | None = None
    ) -> tuple[ReplyIntent, str, str, str, bool]:
        import logging

        log = logging.getLogger(__name__)
        clean_reply = _clean_customer_text(reply_text) or (reply_text or "").strip()[:1500]
        history = (
            self._conversation_history(conversation_id) if conversation_id else "No prior messages"
        )
        last_outbound = self._last_outbound_text(conversation_id)
        deal_memory = self._deal_memory(user_id, history, clean_reply)
        business_context = build_sender_business_context(self.db, user_id, for_replies=True)
        pricing_rules = build_pricing_rules_for_user(self.db, user_id)
        language_rules = language_rules_for_country(None, None, channel="email")
        if conversation_id:
            conv = self.repo.get_conversation(user_id, conversation_id)
            if conv and conv.lead_id:
                lead = self.lead_repo.get_by_id(user_id, conv.lead_id)
                if lead:
                    language_rules = language_rules_for_country(
                        lead.country, lead.city, channel="email"
                    )
        groq = GroqService(self.db, user_id)

        prompts = [
            safe_prompt_format(
                REPLY_ANALYSIS_PROMPT,
                business_context=business_context[:2800],
                reply_text=clean_reply[:1200],
                conversation_history=history[:3600],
                pricing_rules=pricing_rules,
                language_rules=language_rules,
                deal_memory=deal_memory,
                last_outbound=last_outbound,
            ),
            safe_prompt_format(
                SIMPLE_REPLY_PROMPT,
                business_context=business_context[:1800],
                reply_text=clean_reply[:1000],
                conversation_history=history[:2800],
                pricing_rules=pricing_rules,
                language_rules=language_rules,
                deal_memory=deal_memory,
                last_outbound=last_outbound,
            ),
        ]

        last_err: Exception | None = None
        for prompt in prompts:
            try:
                raw = groq._chat(prompt, max_tokens=240, temperature=0.45)
                data = _parse_llm_json(raw)
                intent_str = str(data.get("intent", "other")).strip().lower()
                try:
                    intent = ReplyIntent(intent_str)
                except ValueError:
                    intent = ReplyIntent.other
                draft_body = sanitize_paid_outreach_message(
                    str(data.get("draft_body") or "").strip()
                )
                if _is_vague_filler(draft_body):
                    raise ValueError(f"vague filler draft: {draft_body[:80]}")
                if last_outbound != "(none yet)" and _is_near_duplicate(draft_body, last_outbound):
                    raise ValueError("duplicate of last outbound")
                if len(draft_body) > 320:
                    draft_body = draft_body[:317].rsplit(" ", 1)[0] + "..."
                return (
                    intent,
                    str(data.get("summary") or "Reply received").strip()[:500],
                    str(data.get("draft_subject") or "Re: your message").strip()[:500],
                    draft_body,
                    True,
                )
            except Exception as exc:
                last_err = exc
                log.warning("AI reply analysis attempt failed: %s", exc)
                continue

        log.error("AI reply analysis exhausted retries: %s", last_err)
        return (
            ReplyIntent.question,
            "Customer question",
            "Re: your message",
            self._contextual_fallback_body(
                user_id,
                clean_reply,
                last_outbound=last_outbound if last_outbound != "(none yet)" else "",
            ),
            False,
        )

    def approve_draft(
        self,
        user_id: int,
        draft_id: int,
        *,
        edit_subject: str | None = None,
        edit_body: str | None = None,
        send_immediately: bool = True,
    ) -> None:
        draft = self.repo.get_ai_draft(user_id, draft_id)
        if not draft:
            raise ValueError("Draft not found")

        if edit_subject:
            draft.draft_subject = edit_subject
        if edit_body:
            draft.draft_body = edit_body

        draft.status = AiReplyDraftStatus.approved
        self.db.commit()

        payload = {
            "reply_draft_id": draft.id,
            "conversation_id": draft.conversation_id,
            "subject": draft.draft_subject,
            "body": draft.draft_body,
        }

        if send_immediately:
            try:
                self._send_draft_now(user_id, draft.id)
                return
            except Exception:
                # Fall back to background queue if instant send fails
                pass

        self.queue.enqueue(
            user_id,
            OutreachJobType.send_email,
            payload,
            idempotency_key=f"reply_send_{draft.id}",
        )

    def _send_draft_now(self, user_id: int, draft_id: int) -> None:
        """Send an approved AI draft immediately (no worker wait)."""
        from app.models.email_outreach import AiReplyDraftStatus, ConversationMessage
        from app.models.lead import Lead
        from app.services.email_outreach.transport import send_email

        draft = self.repo.get_ai_draft(user_id, draft_id)
        if not draft:
            raise ValueError("Draft not found")
        conversation = self.repo.get_conversation(user_id, draft.conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")

        account = (
            self.repo.get_account(user_id, conversation.email_account_id)
            if conversation.email_account_id
            else self.repo.get_default_account(user_id)
        )
        if not account:
            raise ValueError("No email account")

        lead = self.db.query(Lead).filter(
            Lead.id == conversation.lead_id, Lead.user_id == user_id
        ).first()
        to_email = (lead.email if lead else "") or ""
        if not to_email:
            raise ValueError("Lead has no email")

        body = (draft.draft_body or "").strip()
        if _is_vague_filler(body):
            last_inbound = (
                self.db.query(ConversationMessage)
                .filter(
                    ConversationMessage.conversation_id == conversation.id,
                    ConversationMessage.direction == "inbound",
                )
                .order_by(ConversationMessage.received_at.desc())
                .first()
            )
            body = self._contextual_fallback_body(
                user_id, (last_inbound.body_text if last_inbound else "") or ""
            )
            draft.draft_body = body

        message_id = send_email(account, to_email, draft.draft_subject, body)
        msg = ConversationMessage(
            conversation_id=conversation.id,
            direction="outbound",
            from_email=account.email_address,
            to_email=to_email,
            subject=draft.draft_subject,
            body_text=body,
            external_message_id=message_id,
            received_at=datetime.now(UTC),
        )
        self.db.add(msg)
        conversation.last_message_at = datetime.now(UTC)
        draft.status = AiReplyDraftStatus.sent
        self.db.commit()
