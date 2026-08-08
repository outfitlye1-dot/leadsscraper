"""WhatsApp manual chat: isolated per-lead/phone storage + deal memory for Brain replies."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.user import User
from app.models.whatsapp_chat import WhatsAppChatMessage, WhatsAppChatThread
from app.repositories.brain_repository import BrainRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.whatsapp_chat import (
    WhatsAppChatContact,
    WhatsAppChatMessageOut,
    WhatsAppChatOpenerResponse,
    WhatsAppChatReplyResponse,
    WhatsAppChatThreadResponse,
    WhatsAppCloudSendResponse,
)
from app.services.email_outreach.sender_profile import build_sender_business_context
from app.services.groq_service import GroqService
from app.services.whatsapp_cloud_service import WhatsAppCloudService
from app.utils.customer_language import language_rules_for_country
from app.utils.outreach_tone import (
    FIRST_MESSAGE_OUTREACH_RULES,
    HUMAN_TOUCH_OUTREACH_RULES,
    build_pricing_rules_for_user,
    resolve_pricing_from_brain,
    sanitize_paid_outreach_message,
    trim_outreach_message,
)
from app.utils.prompt_format import safe_prompt_format

logger = logging.getLogger(__name__)

WHATSAPP_REPLY_PROMPT = """You are chatting on WhatsApp with ONE business customer only.

THREAD LOCK (critical):
- This chat belongs ONLY to: {company} / {contact} / phone {phone}
- Use ONLY the memory + history below for THIS number.
- Never mix in other customers, other deals, or other chats.
- Remember what YOU already said in this thread and continue from there.

Facts about your business (don't invent):
{business_context}

{pricing_rules}

LANGUAGE (critical):
- ALWAYS reply in clear, simple ENGLISH only — even if the customer wrote Urdu, Roman Urdu, Hindi, Arabic, or any other language.
- You may READ and understand any language; your OUTPUT must be English.
- Do not reply in Urdu/Roman Urdu/Hindi.

{deal_memory}

FULL HISTORY FOR THIS NUMBER ONLY:
{history}

Your last message (do NOT repeat):
{last_outbound}

Customer just said:
{customer_message}

Rules:
- Tone: PROFESSIONAL and respectful (B2B). Clear, confident, polite — not slangy, not overly casual.
- READ the customer's latest message carefully and answer THAT (understand Roman Urdu typos: pasa=paisa, bnwani=banwani).
- Sound human. 1–3 short sentences in ENGLISH.
- No price unless they asked OR you already quoted in THIS thread.
- First price ask → HIGH. "less" → lighter package toward mid (>= floor). "ok" → confirm last quoted.
- Never restart the pitch. Never offer free work.
- Never ignore their question to re-introduce yourself.

Reply with ONLY the WhatsApp message text in ENGLISH — no JSON, no labels.
"""

WHATSAPP_FRIENDLY_UNKNOWN_REPLY_PROMPT = """You are {sender_name} chatting on WhatsApp with a potential client (not a saved lead yet).

WHO YOU ARE:
{business_brief}

{pricing_block}

CHAT SO FAR (oldest → newest). "Them" = customer. "You" = your earlier replies:
{history}

THEIR LATEST MESSAGE (this is what you must answer now):
\"\"\"{customer_message}\"\"\"

HOW TO REPLY (critical):
1. Understand their latest message first (any language: Urdu / Roman Urdu / English / mix). Typos: pasa=paisa, bnwani/banwani=want built, ha=hai, mai=main, kitna=how much.
2. Write a natural human WhatsApp reply that directly answers THAT message.
3. ALWAYS reply in clear simple ENGLISH only — never Urdu, Roman Urdu, Hindi, or mixed script.
4. Keep continuity from chat so far — do not suddenly talk about an old topic they did not mention now.
5. 1–3 short sentences. Sound warm and clear.
6. NEVER dump tech stack words (React, Next.js, Django, PostgreSQL, REST, APIs, HTML, CSS).
7. NEVER copy their message back verbatim.
8. NEVER offer free work / free quotes / free trials.
9. If they only greeted (hi/hello/salam): short friendly hello in English + ask how you can help. No pitch dump.
10. If they ask price/kitna: quote opening HIGH from pricing rules in one simple English line + ask scope.
11. If they want a website for something specific (gym/restaurant/etc.): confirm that in English + ask 1 useful detail.
12. You are the seller/helper — NEVER speak in the customer's voice.
13. English only. No Roman Urdu replies.

Output ONLY the WhatsApp reply text in ENGLISH. No quotes, no labels, no JSON.
"""

WHATSAPP_OPENER_PROMPT = """Write a short FIRST WhatsApp message for this ONE local business. Sound human and respectful.

YOUR BUSINESS FACTS:
{business_context}

THIS CONTACT ONLY:
- Company: {company}
- Contact: {contact}
- Phone: {phone}
- City/Country: {location}

{language_rules}
{first_message_rules}
{human_touch}

Rules:
- Follow LANGUAGE rules above for greeting and language
- 2–3 short sentences, under 180 characters
- Introduce who you are + what work you do
- Soft CTA only — NO price / package numbers
- Personalize using this lead's company / city / country — do not use a generic template

Reply with ONLY the message text — no JSON, no labels.
"""

_NUM_RE = re.compile(
    r"(?:\$|usd|pkr|rs\.?\s*)?(\d+(?:[.,]\d+)?)\s*(k|thousand)?",
    re.I,
)


def _serialize(msg: WhatsAppChatMessage) -> WhatsAppChatMessageOut:
    return WhatsAppChatMessageOut(
        id=msg.id,
        lead_id=msg.lead_id,
        direction=msg.direction,
        body=msg.body,
        created_at=msg.created_at,
    )


def _parse_reply_text(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|text)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                reply = str(
                    data.get("reply") or data.get("draft_body") or data.get("body") or ""
                ).strip()
                if reply:
                    return reply
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, dict):
                        reply = str(
                            data.get("reply") or data.get("draft_body") or data.get("body") or ""
                        ).strip()
                        if reply:
                            return reply
                except json.JSONDecodeError:
                    pass
    cleaned = text.strip().strip('"').strip("'")
    cleaned = re.sub(r"^(reply|message|draft)\s*:\s*", "", cleaned, flags=re.I).strip()
    if not cleaned:
        raise ValueError("AI did not return a reply")
    return cleaned


def _extract_number(text: str) -> float | None:
    clean = (text or "").replace(",", "")
    matches = _NUM_RE.findall(clean)
    nums: list[float] = []
    for raw, suffix in matches:
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            continue
        if suffix and suffix.lower() in {"k", "thousand"}:
            val *= 1000
        if 10 <= val <= 10_000_000:
            nums.append(val)
    return nums[-1] if nums else None


_GREETING_RE = re.compile(
    r"^\s*(hi|hello|hey|yo|salam|salaam|assalam[u\s\-]*alaikum|aoa|hi\s+sir|hello\s+sir|"
    r"hello\s+\w{2,20}(\s+(bahi|bhai|bro|sir))?|salam\s+\w{0,20})"
    r"[\s!?.]*$",
    re.I,
)
_PRICE_RE = re.compile(
    r"\b(kitna|kitni|price|cost|fee|rate|budget|pasa|paisa|charges?|how\s+much|quote)\b",
    re.I,
)
_SERVICE_RE = re.compile(
    r"\b(website|web\s*site|bnwani|banwani|bana\s*do|bana\s*wani|app|logo|design|"
    r"landing\s*page|ecommerce|e-?commerce|shop|store|gym|restaurant|need\s+help|"
    r"madad|help\s+chahiye|banwana|banwani)\b",
    re.I,
)
_THANKS_RE = re.compile(
    r"^\s*(thanks|thank\s*you|thx|shukriya|ok|okay|theek|thik|done|ok\s*thanks|thanks\s*ok)"
    r"[\s!?.]*$",
    re.I,
)
_OFFTOPIC_RE = re.compile(
    r"\b(i\s*love\s*you|love\s*you|miss\s*you|marry\s*me|kiss|jaan|baby|handsome|beautiful)\b",
    re.I,
)
_PITCH_SPAM_RE = re.compile(
    r"\b(usd\b|\$\s*\d|next\.?js|django|postgresql|react\.?js|kitna paisa|package\s+roughly|"
    r"700\s*(dollar|usd)?)\b",
    re.I,
)



def _classify_unknown_intent(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "other"
    if _OFFTOPIC_RE.search(raw) and not _SERVICE_RE.search(raw) and not _PRICE_RE.search(raw):
        return "offtopic"
    if _THANKS_RE.match(raw):
        return "thanks"
    if _GREETING_RE.match(raw) and not _PRICE_RE.search(raw) and not _SERVICE_RE.search(raw):
        return "greeting"
    if _PRICE_RE.search(raw):
        return "price"
    if _SERVICE_RE.search(raw):
        return "need_service"
    # Short hello-ish with name: "Hello hamza bahi"
    if len(raw.split()) <= 5 and re.search(r"\b(hi|hello|hey|salam)\b", raw, re.I):
        if not _PRICE_RE.search(raw) and not _SERVICE_RE.search(raw):
            return "greeting"
    return "other"


def _guess_service_topic(text: str) -> str | None:
    low = (text or "").lower()
    for key in (
        "gym",
        "restaurant",
        "hotel",
        "salon",
        "shop",
        "clinic",
        "school",
        "cafe",
        "bakery",
        "barber",
    ):
        if key in low:
            return key
    if re.search(r"\b(website|web\s*site|bnwani|banwani)\b", low):
        return "website"
    return None


def _services_one_liner(db, user_id: int) -> str:
    brain = BrainRepository(db).get_by_user(user_id)
    if brain and brain.services:
        cleaned = [str(v).strip() for v in brain.services if str(v).strip()]
        if cleaned:
            return ", ".join(cleaned[:6])
    if brain and brain.name:
        return f"{brain.name} — websites & digital work"
    return "websites and digital services"


def _wa_sender_name(db, user_id: int) -> str:
    brain = BrainRepository(db).get_by_user(user_id)
    name = (getattr(brain, "name", None) or "").strip()
    return name or "I"


_TECH_NOISE_RE = re.compile(
    r"\b(react(?:\.?js)?|next\.?js|django|postgresql|postgres|rest\s*apis?|"
    r"html5?|css3?|javascript|node\.?js|tailwind|typescript|mongodb|fastapi)\b",
    re.I,
)


def _wa_business_brief(db, user_id: int) -> str:
    """Short WhatsApp-safe business facts — no raw tech stack dump."""
    brain = BrainRepository(db).get_by_user(user_id)
    parts: list[str] = []
    if brain and brain.name:
        parts.append(f"Name: {brain.name.strip()}")
    services = []
    if brain and brain.services:
        services = [str(v).strip() for v in brain.services if str(v).strip()][:8]
    if services:
        parts.append(f"Services: {', '.join(services)}")
    else:
        parts.append("Services: website development and maintenance")
    if brain and brain.professional_summary:
        summary = _TECH_NOISE_RE.sub("", brain.professional_summary.strip())
        summary = re.sub(r"\s{2,}", " ", summary).strip(" ,.-")
        if summary:
            parts.append(f"About: {summary[:280]}")
    return "\n".join(parts) if parts else "Services: website development"


def _format_web_history(history: str, limit: int = 6) -> str:
    """Normalize job history into Them/You lines; drop spammy old AI pitches."""
    lines_out: list[str] = []
    for line in (history or "").splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^\d+\.\s*", "", s)
        if re.search(r"(?i)\bCustomer\b", s) or s.lower().startswith("customer:"):
            body = re.sub(r"(?i)^.*Customer\s*:\s*", "", s).strip()
            if body:
                lines_out.append(f"Them: {body[:200]}")
        elif re.search(r"(?i)\bYou\b", s) or s.lower().startswith("you"):
            body = re.sub(r"(?i)^.*You(?:\s*\(already sent\))?\s*:\s*", "", s).strip()
            if not body:
                continue
            # Skip old spam pitches so they don't poison the next reply
            if _PITCH_SPAM_RE.search(body) or _TECH_NOISE_RE.search(body) or len(body) > 220:
                continue
            lines_out.append(f"You: {body[:200]}")
    return "\n".join(lines_out[-limit:]) if lines_out else "(no earlier messages)"


def _customer_only_history(history: str, limit: int = 3) -> str:
    lines: list[str] = []
    for line in (history or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if re.search(r"\bCustomer\b", s, re.I) or s.lower().startswith("customer:"):
            cleaned = re.sub(r"^\d+\.\s*", "", s)
            cleaned = re.sub(r"(?i)^customer\s*:\s*", "", cleaned).strip()
            if cleaned:
                lines.append(f"- {cleaned[:180]}")
    return "\n".join(lines[-limit:])


def _scrub_unknown_reply(reply: str, *, customer_message: str, intent: str) -> str:
    text = (reply or "").strip()
    if not text:
        return ""
    low = text.lower()
    cust = (customer_message or "").strip()
    if cust and (low == cust.lower() or low.startswith(cust.lower() + " ")):
        text = text[len(cust) :].lstrip(" ,.-:")
    text = _TECH_NOISE_RE.sub("", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,.-")
    if intent != "price" and _PITCH_SPAM_RE.search(text):
        return ""
    return text


class WhatsAppChatService:
    def __init__(self, db: Session):
        self.db = db
        self.lead_repo = LeadRepository(db)

    def _require_saved_phone_lead(self, user: User, lead_id: int) -> Lead:
        lead = self.lead_repo.get_by_id(user.id, lead_id)
        if not lead or not lead.is_saved:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved lead not found")
        phone = (lead.phone or "").strip()
        if not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This lead has no phone number",
            )
        return lead

    def _get_or_create_thread(self, user: User, lead: Lead) -> WhatsAppChatThread:
        phone = (lead.phone or "").strip()
        thread = (
            self.db.query(WhatsAppChatThread)
            .filter(
                WhatsAppChatThread.user_id == user.id,
                WhatsAppChatThread.lead_id == lead.id,
            )
            .first()
        )
        if thread:
            if phone and thread.phone != phone:
                thread.phone = phone
            return thread
        thread = WhatsAppChatThread(
            user_id=user.id,
            lead_id=lead.id,
            phone=phone,
            memory_summary=None,
            deal_status="new",
        )
        self.db.add(thread)
        self.db.flush()
        # Attach any orphan messages for this lead
        (
            self.db.query(WhatsAppChatMessage)
            .filter(
                WhatsAppChatMessage.user_id == user.id,
                WhatsAppChatMessage.lead_id == lead.id,
                WhatsAppChatMessage.thread_id.is_(None),
            )
            .update(
                {"thread_id": thread.id, "phone": phone},
                synchronize_session=False,
            )
        )
        return thread

    def _build_deal_memory(self, user_id: int, thread: WhatsAppChatThread, history: str) -> str:
        brain = BrainRepository(self.db).get_by_user(user_id)
        high, floor, currency = resolve_pricing_from_brain(brain)
        our_nums: list[float] = []
        their_nums: list[float] = []
        for line in (history or "").splitlines():
            low = line.strip()
            if low.startswith("You:"):
                n = _extract_number(low)
                if n is not None and floor <= n <= high * 1.2:
                    our_nums.append(n)
            elif low.startswith("Customer:"):
                n = _extract_number(low)
                if n is not None and 10 <= n <= high * 1.5:
                    their_nums.append(n)

        last_our = thread.last_price_quoted if thread.last_price_quoted is not None else (
            our_nums[-1] if our_nums else None
        )
        last_their = thread.customer_budget if thread.customer_budget is not None else (
            their_nums[-1] if their_nums else None
        )

        bits = [
            "DEAL MEMORY FOR THIS PHONE ONLY (OBEY):",
            f"- Thread phone: {thread.phone}",
            f"- Deal status: {thread.deal_status or 'new'}",
        ]
        if thread.memory_summary:
            bits.append(f"- Saved notes: {thread.memory_summary.strip()[:500]}")
        if last_our is not None:
            bits.append(
                f"- You already quoted about {currency} {last_our:g}. "
                f"Do NOT reset to HIGH ({currency} {high:g}). "
                f"Stay <= {last_our:g} and >= floor {currency} {floor:g}."
            )
        else:
            bits.append(
                f"- No price quoted yet by you — first ask may open at HIGH {currency} {high:g}."
            )
        if last_their is not None:
            bits.append(
                f"- Customer mentioned about {currency} {last_their:g} — respond to that."
            )
        bits.append("- Continue THIS deal only. Never restart cold. Never use another chat.")
        return "\n".join(bits)

    def _refresh_thread_memory(
        self,
        thread: WhatsAppChatThread,
        *,
        customer_text: str = "",
        outbound_text: str = "",
    ) -> None:
        notes: list[str] = []
        if thread.memory_summary:
            notes.append(thread.memory_summary.strip())

        cust_n = _extract_number(customer_text)
        if cust_n is not None:
            thread.customer_budget = cust_n
            notes.append(f"Customer mentioned ~{cust_n:g}")

        our_n = _extract_number(outbound_text)
        if our_n is not None:
            thread.last_price_quoted = our_n
            notes.append(f"You quoted ~{our_n:g}")

        low = f"{customer_text} {outbound_text}".lower()
        if any(k in low for k in ("ok", "okay", "deal", "sounds good", "let's do", "lock")):
            thread.deal_status = "agreed"
            notes.append("Customer leaned toward yes / lock")
        elif any(k in low for k in ("less", "expensive", "discount", "kam", "sasta", "budget")):
            thread.deal_status = "negotiating"
            notes.append("Price negotiation")
        elif any(k in low for k in ("price", "cost", "how much", "kitna", "package", "fee")):
            thread.deal_status = thread.deal_status or "pricing"
            notes.append("Price discussed")
        elif thread.deal_status in (None, "new") and outbound_text:
            thread.deal_status = "open"

        # Keep last few unique notes
        seen: set[str] = set()
        uniq: list[str] = []
        for n in notes:
            key = n.lower()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(n)
        thread.memory_summary = " · ".join(uniq[-8:])[:900] or None
        thread.updated_at = datetime.now(UTC)

    def list_contacts(self, user: User) -> list[WhatsAppChatContact]:
        leads, _ = self.lead_repo.search(
            user_id=user.id,
            saved=True,
            page=1,
            page_size=500,
            include_background=True,
        )
        phone_leads = [l for l in leads if (l.phone or "").strip()]
        if not phone_leads:
            return []

        lead_ids = [l.id for l in phone_leads]
        rows = (
            self.db.query(
                WhatsAppChatMessage.lead_id,
                func.count(WhatsAppChatMessage.id),
                func.max(WhatsAppChatMessage.id),
            )
            .filter(
                WhatsAppChatMessage.user_id == user.id,
                WhatsAppChatMessage.lead_id.in_(lead_ids),
            )
            .group_by(WhatsAppChatMessage.lead_id)
            .all()
        )
        stats = {lid: (cnt, max_id) for lid, cnt, max_id in rows}
        last_bodies: dict[int, WhatsAppChatMessage] = {}
        max_ids = [max_id for _, max_id in stats.values() if max_id]
        if max_ids:
            for msg in (
                self.db.query(WhatsAppChatMessage)
                .filter(WhatsAppChatMessage.id.in_(max_ids))
                .all()
            ):
                last_bodies[msg.lead_id] = msg

        contacts: list[WhatsAppChatContact] = []
        for lead in phone_leads:
            cnt, _ = stats.get(lead.id, (0, None))
            last = last_bodies.get(lead.id)
            contacts.append(
                WhatsAppChatContact(
                    lead_id=lead.id,
                    company_name=lead.company_name,
                    contact_name=lead.contact_name,
                    phone=(lead.phone or "").strip(),
                    city=lead.city,
                    country=lead.country,
                    last_message=(last.body[:120] if last else None),
                    last_message_at=last.created_at if last else None,
                    message_count=int(cnt or 0),
                )
            )

        contacts.sort(
            key=lambda c: (c.last_message_at is not None, c.last_message_at or "", c.company_name or ""),
            reverse=True,
        )
        return contacts

    def get_thread(self, user: User, lead_id: int) -> WhatsAppChatThreadResponse:
        lead = self._require_saved_phone_lead(user, lead_id)
        thread = self._get_or_create_thread(user, lead)
        self.db.commit()
        messages = (
            self.db.query(WhatsAppChatMessage)
            .filter(
                WhatsAppChatMessage.user_id == user.id,
                WhatsAppChatMessage.lead_id == lead_id,
            )
            .order_by(WhatsAppChatMessage.created_at.asc(), WhatsAppChatMessage.id.asc())
            .limit(300)
            .all()
        )
        return WhatsAppChatThreadResponse(
            lead_id=lead.id,
            company_name=lead.company_name,
            contact_name=lead.contact_name,
            phone=(lead.phone or "").strip(),
            city=lead.city,
            country=lead.country,
            memory_summary=thread.memory_summary,
            last_price_quoted=thread.last_price_quoted,
            customer_budget=thread.customer_budget,
            deal_status=thread.deal_status,
            messages=[_serialize(m) for m in messages],
        )

    def _history_text(self, user_id: int, lead_id: int) -> tuple[str, str]:
        messages = (
            self.db.query(WhatsAppChatMessage)
            .filter(
                WhatsAppChatMessage.user_id == user_id,
                WhatsAppChatMessage.lead_id == lead_id,
            )
            .order_by(WhatsAppChatMessage.created_at.desc(), WhatsAppChatMessage.id.desc())
            .limit(40)
            .all()
        )
        messages = list(reversed(messages))
        lines: list[str] = []
        last_outbound = "(none yet)"
        for m in messages:
            if m.direction == "outbound":
                lines.append(f"You: {m.body.strip()[:320]}")
                if m.body.strip():
                    last_outbound = m.body.strip()[:320]
            else:
                lines.append(f"Customer: {m.body.strip()[:320]}")
        return ("\n".join(lines) if lines else "No prior messages"), last_outbound

    def _generate_reply(
        self,
        user: User,
        lead: Lead,
        thread: WhatsAppChatThread,
        customer_message: str,
    ) -> str:
        history, last_outbound = self._history_text(user.id, lead.id)
        # Include the new customer message in history for memory extraction context
        history_for_prompt = history
        if customer_message.strip():
            history_for_prompt = (
                f"{history}\nCustomer: {customer_message.strip()[:320]}"
                if history != "No prior messages"
                else f"Customer: {customer_message.strip()[:320]}"
            )
        deal_memory = self._build_deal_memory(user.id, thread, history_for_prompt)
        # WhatsApp-safe brief — raw Brain skills dump makes the model spam tech names
        business_context = _wa_business_brief(self.db, user.id)
        pricing_rules = build_pricing_rules_for_user(self.db, user.id)
        location = ", ".join(p for p in [lead.city, lead.country] if p) or "—"
        prompt = safe_prompt_format(
            WHATSAPP_REPLY_PROMPT,
            business_context=business_context,
            company=lead.company_name or "the business",
            contact=lead.contact_name or "there",
            phone=thread.phone,
            location=location,
            pricing_rules=pricing_rules[:900],
            deal_memory=deal_memory,
            history=history[-2800:],
            last_outbound=(last_outbound or "(none)")[:280],
            customer_message=customer_message.strip()[:900],
        )
        groq = GroqService(self.db, user.id)
        raw = groq._chat(prompt, max_tokens=150, temperature=0.4, fast=False)
        reply = sanitize_paid_outreach_message(
            trim_outreach_message(_parse_reply_text(raw), max_chars=360)
        )
        if reply:
            reply = _TECH_NOISE_RE.sub("", reply)
            reply = re.sub(r"\s{2,}", " ", reply).strip(" ,.-")
        if not reply:
            raise ValueError("empty reply")
        return reply

    def generate_friendly_unknown_reply(
        self,
        user: User,
        *,
        customer_message: str,
        chat_title: str = "",
        phone: str | None = None,
        history: str = "",
    ) -> str:
        """AI reads the inbound message, then generates a fresh reply (no canned templates)."""
        _ = phone
        text = (customer_message or "").strip()
        if not text:
            raise ValueError("empty customer message")

        asked_price = bool(_PRICE_RE.search(text))
        intent = _classify_unknown_intent(text)
        # Greetings / offtopic must not pull old restaurant/gym topics from history
        if intent in {"greeting", "offtopic", "thanks"}:
            hist_block = "(no earlier messages)"
        else:
            hist_block = _format_web_history(history, limit=6)

        if asked_price:
            high, _floor, currency = resolve_pricing_from_brain(
                BrainRepository(self.db).get_by_user(user.id)
            )
            pricing_block = (
                f"They asked price. Quote opening HIGH once as '{currency} {high:g}'. "
                "One short line what it covers, then ask scope (pages/features). "
                "Do not repeat their question. Do not list tech tools."
            )
        else:
            pricing_block = (
                "They did NOT ask price — do NOT mention any USD/PKR/$ numbers or packages."
            )

        prompt = safe_prompt_format(
            WHATSAPP_FRIENDLY_UNKNOWN_REPLY_PROMPT,
            sender_name=_wa_sender_name(self.db, user.id),
            business_brief=_wa_business_brief(self.db, user.id),
            pricing_block=pricing_block,
            history=hist_block,
            customer_message=text[:900],
        )
        if chat_title:
            prompt = f"Chat title on WhatsApp: {chat_title[:60]}\n\n" + prompt

        logger.info(
            "WA Web AI-read reply (random) intent=%s msg=%r price_ask=%s",
            intent,
            text[:80],
            asked_price,
        )

        groq = GroqService(self.db, user.id)
        raw = groq._chat(prompt, max_tokens=160, temperature=0.35, fast=False)
        reply = sanitize_paid_outreach_message(
            trim_outreach_message(_parse_reply_text(raw), max_chars=340)
        )
        reply = _scrub_unknown_reply(reply or "", customer_message=text, intent=intent)

        # Strip leading echo of their question ("Kitna paisa lo ga, …")
        if reply:
            echo = re.match(
                re.escape(text[:40]) + r"[\s,.\-:]*",
                reply,
                flags=re.I,
            )
            if echo:
                reply = reply[echo.end() :].lstrip(" ,.-")
            # Common Roman Urdu echo of price ask
            reply = re.sub(
                r"(?i)^(kitna\s+pas[aei]\s+lo\s+ga|kitna\s+paisa\s+lo\s+ga)[\s,.\-:]*",
                "",
                reply,
            ).strip()

        bad = (
            (not reply)
            or (not asked_price and _PITCH_SPAM_RE.search(reply or ""))
            or (intent == "greeting" and _PITCH_SPAM_RE.search(reply or ""))
            or (intent == "offtopic" and re.search(r"(?i)\b(website|gym|restaurant|usd)\b", reply or ""))
        )
        if bad:
            retry = (
                f"You are {_wa_sender_name(self.db, user.id)}. "
                "Read ONLY this WhatsApp message and reply in 1–2 natural short ENGLISH sentences. "
                "Do not mention older chat topics. "
                "Always English — never Urdu or Roman Urdu. "
                "No prices unless they asked. No React/Next/Django/Postgres.\n\n"
                f"Message: {text[:500]}\n\nONLY the English reply text:"
            )
            raw2 = groq._chat(retry, max_tokens=100, temperature=0.3, fast=False)
            reply = sanitize_paid_outreach_message(
                trim_outreach_message(_parse_reply_text(raw2), max_chars=300)
            )
            reply = _scrub_unknown_reply(reply or "", customer_message=text, intent=intent)

        if not reply or len(reply.strip()) < 3:
            raise ValueError("AI returned empty reply after reading message")
        return reply.strip()

    def compose_web_auto_reply(
        self,
        user: User,
        *,
        customer_message: str,
        chat_title: str = "",
        phone_hint: str | None = None,
        lead: Lead | None = None,
        history: str = "",
    ) -> tuple[str, str, int | None]:
        """AI checks lead vs random, reads message, returns (reply, mode, lead_id)."""
        text = (customer_message or "").strip()
        if not text:
            raise ValueError("empty customer message")

        if lead is not None:
            result = self.reply(user, int(lead.id), text)
            return result.reply.body, "professional_lead", int(lead.id)

        reply = self.generate_friendly_unknown_reply(
            user,
            customer_message=text,
            chat_title=chat_title,
            phone=phone_hint,
            history=history,
        )
        return reply, "friendly_random", None

    def _generate_opener(
        self,
        user: User,
        lead: Lead,
        phone: str,
        *,
        force_english: bool = False,
    ) -> str:
        business_context = build_sender_business_context(self.db, user.id, for_replies=False)[:1000]
        location = ", ".join(p for p in [lead.city, lead.country] if p) or "—"
        if force_english:
            language_rules = (
                "LANGUAGE (critical):\n"
                "- Write the ENTIRE message in clear professional English only.\n"
                "- Never use Urdu, Roman Urdu, Arabic script, or any other language.\n"
                '- Start with a short English greeting like "Hi," or "Hi sir,".'
            )
        else:
            language_rules = language_rules_for_country(lead.country, lead.city, channel="whatsapp")
        prompt = safe_prompt_format(
            WHATSAPP_OPENER_PROMPT,
            business_context=business_context,
            company=lead.company_name or "the business",
            contact=lead.contact_name or "there",
            phone=phone,
            location=location,
            language_rules=language_rules,
            first_message_rules=FIRST_MESSAGE_OUTREACH_RULES,
            human_touch=HUMAN_TOUCH_OUTREACH_RULES,
        )
        groq = GroqService(self.db, user.id)
        raw = groq._chat(prompt, max_tokens=100, temperature=0.7, fast=True)
        reply = sanitize_paid_outreach_message(
            trim_outreach_message(_parse_reply_text(raw), max_chars=220)
        )
        if not reply:
            raise ValueError("empty opener")
        return reply

    def _save(
        self,
        user_id: int,
        lead_id: int,
        direction: str,
        body: str,
        *,
        thread: WhatsAppChatThread | None = None,
        phone: str | None = None,
        commit: bool = True,
    ) -> WhatsAppChatMessage:
        msg = WhatsAppChatMessage(
            user_id=user_id,
            lead_id=lead_id,
            thread_id=thread.id if thread else None,
            phone=phone or (thread.phone if thread else None),
            direction=direction,
            body=body.strip(),
        )
        self.db.add(msg)
        if commit:
            self.db.commit()
            self.db.refresh(msg)
        else:
            self.db.flush()
        return msg

    def reply(
        self,
        user: User,
        lead_id: int,
        customer_message: str,
        hint: str | None = None,
    ) -> WhatsAppChatReplyResponse:
        lead = self._require_saved_phone_lead(user, lead_id)
        thread = self._get_or_create_thread(user, lead)
        text = (customer_message or "").strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paste the customer message")

        try:
            reply_text = self._generate_reply(user, lead, thread, text)
        except Exception as exc:
            logger.warning("WhatsApp reply AI failed: %s", exc)
            high, floor, currency = resolve_pricing_from_brain(
                BrainRepository(self.db).get_by_user(user.id)
            )
            low = text.lower()
            quoted = thread.last_price_quoted
            if any(k in low for k in ("price", "cost", "how much", "kitna", "package", "fee")):
                if quoted is not None:
                    reply_text = (
                        f"As I mentioned, we're around {currency} {quoted:g}. "
                        "Want to lock that in?"
                    )
                else:
                    reply_text = (
                        f"Sure — a solid package is about {currency} {high:g}. "
                        "Want me to walk you through what's included?"
                    )
            elif any(k in low for k in ("less", "expensive", "discount", "kam", "sasta")):
                mid = (high + floor) / 2
                base = quoted if quoted is not None else high
                offer = min(base, mid)
                reply_text = (
                    f"I can do a lighter package around {currency} {offer:g} "
                    "if we keep scope simple. Does that work?"
                )
            elif any(k in low for k in ("ok", "okay", "sounds good", "deal", "haan")):
                lock = quoted if quoted is not None else high
                reply_text = (
                    f"Perfect — let's lock it at {currency} {lock:g}. "
                    "Send me your details and I'll get started."
                )
            else:
                reply_text = (
                    "Got it — happy to help. What do you need most for your business right now?"
                )
            reply_text = sanitize_paid_outreach_message(reply_text)

        inbound = self._save(
            user.id, lead.id, "inbound", text, thread=thread, phone=thread.phone, commit=False
        )
        outbound = self._save(
            user.id, lead.id, "outbound", reply_text, thread=thread, phone=thread.phone, commit=False
        )
        self._refresh_thread_memory(thread, customer_text=text, outbound_text=reply_text)
        self.db.commit()
        self.db.refresh(inbound)
        self.db.refresh(outbound)
        return WhatsAppChatReplyResponse(customer=_serialize(inbound), reply=_serialize(outbound))

    def draft_opener(self, user: User, lead_id: int) -> WhatsAppChatOpenerResponse:
        lead = self._require_saved_phone_lead(user, lead_id)
        thread = self._get_or_create_thread(user, lead)
        existing = (
            self.db.query(WhatsAppChatMessage.id)
            .filter(
                WhatsAppChatMessage.user_id == user.id,
                WhatsAppChatMessage.lead_id == lead_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat already started — paste their reply instead",
            )
        try:
            reply_text = self._generate_opener(user, lead, thread.phone)
        except Exception as exc:
            logger.warning("WhatsApp opener AI failed: %s", exc)
            company = lead.company_name or "your business"
            reply_text = sanitize_paid_outreach_message(
                f"Hi sir, I saw {company} and help local businesses with websites "
                f"and online presence. Open to a quick chat?"
            )

        outbound = self._save(
            user.id, lead.id, "outbound", reply_text, thread=thread, phone=thread.phone, commit=False
        )
        self._refresh_thread_memory(thread, outbound_text=reply_text)
        thread.deal_status = "open"
        self.db.commit()
        self.db.refresh(outbound)
        return WhatsAppChatOpenerResponse(reply=_serialize(outbound))

    def save_manual_outbound(self, user: User, lead_id: int, body: str) -> WhatsAppChatOpenerResponse:
        lead = self._require_saved_phone_lead(user, lead_id)
        thread = self._get_or_create_thread(user, lead)
        text = sanitize_paid_outreach_message((body or "").strip())
        if not text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Write your message first")
        outbound = self._save(
            user.id, lead.id, "outbound", text, thread=thread, phone=thread.phone, commit=False
        )
        self._refresh_thread_memory(thread, outbound_text=text)
        if not thread.deal_status or thread.deal_status == "new":
            thread.deal_status = "open"
        self.db.commit()
        self.db.refresh(outbound)
        return WhatsAppChatOpenerResponse(reply=_serialize(outbound))

    def clear_thread(self, user: User, lead_id: int) -> dict[str, int]:
        lead = self._require_saved_phone_lead(user, lead_id)
        deleted = (
            self.db.query(WhatsAppChatMessage)
            .filter(
                WhatsAppChatMessage.user_id == user.id,
                WhatsAppChatMessage.lead_id == lead_id,
            )
            .delete(synchronize_session=False)
        )
        thread = (
            self.db.query(WhatsAppChatThread)
            .filter(
                WhatsAppChatThread.user_id == user.id,
                WhatsAppChatThread.lead_id == lead.id,
            )
            .first()
        )
        if thread:
            thread.memory_summary = None
            thread.last_price_quoted = None
            thread.customer_budget = None
            thread.deal_status = "new"
            thread.updated_at = datetime.now(UTC)
        self.db.commit()
        return {"deleted": int(deleted or 0)}

    def send_via_cloud(
        self,
        user: User,
        lead_id: int,
        *,
        body: str | None = None,
        message_id: int | None = None,
        mode: str = "text",
        template_name: str | None = None,
        language_code: str = "en_US",
    ) -> WhatsAppCloudSendResponse:
        """Send via Meta WhatsApp Cloud API and keep a local outbound copy."""
        lead = self._require_saved_phone_lead(user, lead_id)
        thread = self._get_or_create_thread(user, lead)
        cloud = WhatsAppCloudService()

        local_msg: WhatsAppChatMessage | None = None
        text = (body or "").strip()
        if message_id is not None:
            local_msg = (
                self.db.query(WhatsAppChatMessage)
                .filter(
                    WhatsAppChatMessage.id == message_id,
                    WhatsAppChatMessage.user_id == user.id,
                    WhatsAppChatMessage.lead_id == lead_id,
                )
                .first()
            )
            if not local_msg:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
            text = (local_msg.body or "").strip()

        mode_norm = (mode or "text").strip().lower()
        if mode_norm == "template":
            result = cloud.send_template(
                to_phone=thread.phone,
                template_name=template_name or "hello_world",
                language_code=language_code or "en_US",
            )
            # Keep a local note so the thread shows what was sent
            note = f"[Template sent: {template_name or 'hello_world'}]"
            if not local_msg:
                local_msg = self._save(
                    user.id,
                    lead.id,
                    "outbound",
                    note,
                    thread=thread,
                    phone=thread.phone,
                    commit=False,
                )
                self._refresh_thread_memory(thread, outbound_text=note)
                self.db.commit()
                self.db.refresh(local_msg)
        else:
            if not text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nothing to send — provide body or message_id",
                )
            result = cloud.send_text(to_phone=thread.phone, body=text)
            if not local_msg:
                local_msg = self._save(
                    user.id,
                    lead.id,
                    "outbound",
                    text,
                    thread=thread,
                    phone=thread.phone,
                    commit=False,
                )
                self._refresh_thread_memory(thread, outbound_text=text)
                self.db.commit()
                self.db.refresh(local_msg)

        return WhatsAppCloudSendResponse(
            success=True,
            message_id=result.get("message_id"),
            to=result.get("to"),
            local_message_id=local_msg.id if local_msg else None,
            detail="Sent via WhatsApp Cloud API",
        )

    def _phone_digits_match(self, a: str, b: str) -> bool:
        da = re.sub(r"\D", "", a or "")
        db = re.sub(r"\D", "", b or "")
        if not da or not db or min(len(da), len(db)) < 8:
            return False
        return da == db or da.endswith(db[-10:]) or db.endswith(da[-10:])

    def _find_lead_by_phone_digits(self, digits: str) -> Lead | None:
        """Match inbound WhatsApp to a lead without leaking across user accounts.

        Order:
        1) Existing WhatsAppChatThread for this phone (already tenant-bound)
        2) Saved leads with matching phone — only if exactly one user owns matches
        3) If multiple users share the number, pick the user with the most recent
           outbound WhatsApp message to that phone (they started the Cloud chat)
        """
        if not digits or len(digits) < 8:
            return None

        # 1) Prefer existing threads (scoped by user_id on the row)
        threads = (
            self.db.query(WhatsAppChatThread)
            .filter(WhatsAppChatThread.phone.isnot(None), WhatsAppChatThread.phone != "")
            .order_by(WhatsAppChatThread.updated_at.desc())
            .limit(500)
            .all()
        )
        for thread in threads:
            if not self._phone_digits_match(thread.phone, digits):
                continue
            lead = (
                self.db.query(Lead)
                .filter(Lead.id == thread.lead_id, Lead.user_id == thread.user_id)
                .first()
            )
            if lead:
                return lead

        # 2) Collect matching saved leads, grouped by owner
        candidates = (
            self.db.query(Lead)
            .filter(Lead.is_saved.is_(True), Lead.phone.isnot(None), Lead.phone != "")
            .order_by(Lead.id.desc())
            .limit(2000)
            .all()
        )
        by_user: dict[int, list[Lead]] = {}
        for lead in candidates:
            if not self._phone_digits_match(lead.phone or "", digits):
                continue
            by_user.setdefault(int(lead.user_id), []).append(lead)

        if not by_user:
            return None
        if len(by_user) == 1:
            return next(iter(by_user.values()))[0]

        # 3) Ambiguous across tenants — use most recent outbound WA message owner
        recent_out = (
            self.db.query(WhatsAppChatMessage)
            .filter(
                WhatsAppChatMessage.direction == "outbound",
                WhatsAppChatMessage.phone.isnot(None),
            )
            .order_by(WhatsAppChatMessage.created_at.desc())
            .limit(800)
            .all()
        )
        for msg in recent_out:
            if msg.user_id not in by_user:
                continue
            if not self._phone_digits_match(msg.phone or "", digits):
                continue
            return by_user[int(msg.user_id)][0]

        logger.warning(
            "WA inbound phone %s matches %s users — skipping to avoid cross-account leak",
            digits[-4:],
            len(by_user),
        )
        return None

    def ingest_cloud_webhook(self, payload: dict) -> dict:
        """Parse Meta webhook payload and store inbound texts into the matching chat thread."""
        stored = 0
        statuses = 0
        if not isinstance(payload, dict):
            return {"stored": 0, "statuses": 0}

        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for st in value.get("statuses") or []:
                    statuses += 1
                    logger.info(
                        "WA status %s for %s",
                        st.get("status"),
                        st.get("recipient_id") or st.get("id"),
                    )

                for msg in value.get("messages") or []:
                    if not isinstance(msg, dict):
                        continue
                    from_phone = str(msg.get("from") or "").strip()
                    msg_type = str(msg.get("type") or "").strip()
                    body = ""
                    if msg_type == "text":
                        body = str((msg.get("text") or {}).get("body") or "").strip()
                    elif msg_type == "button":
                        body = str((msg.get("button") or {}).get("text") or "").strip()
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive") or {}
                        body = str(
                            (interactive.get("button_reply") or {}).get("title")
                            or (interactive.get("list_reply") or {}).get("title")
                            or ""
                        ).strip()
                    else:
                        body = f"[{msg_type} message received]"

                    if not from_phone or not body:
                        continue

                    lead = self._find_lead_by_phone_digits(re.sub(r"\D", "", from_phone))
                    if not lead or not lead.user_id:
                        logger.info("WA inbound from %s — no matching saved lead", from_phone)
                        continue

                    # Synthetic user object for helpers
                    user = self.db.query(User).filter(User.id == lead.user_id).first()
                    if not user:
                        continue
                    thread = self._get_or_create_thread(user, lead)
                    self._save(
                        user.id,
                        lead.id,
                        "inbound",
                        body,
                        thread=thread,
                        phone=thread.phone,
                        commit=False,
                    )
                    self._refresh_thread_memory(thread, customer_text=body)
                    stored += 1

        if stored:
            self.db.commit()
        return {"stored": stored, "statuses": statuses}
