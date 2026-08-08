"""AI-powered personalized email generation for outreach."""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.services.groq_service import GroqService
from app.utils.customer_language import language_rules_for_country
from app.utils.outreach_tone import (
    FIRST_MESSAGE_OUTREACH_RULES,
    sanitize_paid_outreach_message,
    trim_outreach_message,
)
from app.utils.prompt_format import safe_prompt_format
from app.services.email_outreach.sender_profile import build_sender_business_context


OUTREACH_EMAIL_PROMPT = """You are writing a short FIRST outreach email for a freelancer/agency selling paid digital services to a local small business.

SENDER PROFILE:
{sender_profile}

LEAD CONTEXT:
- Company: {company_name}
- Contact: {contact_name}
- Industry: {industry}
- Website: {website}
- City/Country: {location}
- Pain points / website issues: {pain_points}
- Buying intent: {buying_intent}
- Recommended service: {recommended_service}
- Previous interactions: {previous_interactions}

{language_rules}

RULES:
- Write like a real person, not a marketing template
- Keep body under 90 words
- Use the greeting from LANGUAGE rules (even if no personal name)
- Introduce who you are + what work you do for businesses like theirs
- Soft CTA only (chat / how you can help)
- DO NOT mention any price, fee, package cost, or number in this first email
- Pricing comes later only when THEY ask
{first_message_rules}
- Reference something specific about their business when possible
- Casual-professional tone — contractions, short lines, human touch
- No buzzwords or corporate fluff
{follow_up_hint}

Return ONLY valid JSON:
{{"subject": "...", "body": "..."}}
"""


class EmailGenerationService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.groq = GroqService(db, user_id)

    def _sender_profile(self) -> str:
        return build_sender_business_context(self.db, self.user_id)

    def _pain_points(self, lead: Lead) -> str:
        problems = lead.website_problems or []
        if problems:
            return ", ".join(str(p) for p in problems[:5])
        if lead.website_opportunity_score and lead.website_opportunity_score >= 60:
            return "Weak or missing web presence"
        return "Unknown — infer from industry"

    def _previous_interactions(self, lead: Lead) -> str:
        from app.models.email_outreach import ConversationMessage, EmailConversation
        from app.repositories.email_outreach_repository import EmailOutreachRepository
        from app.repositories.message_repository import MessageRepository

        parts: list[str] = []
        conversation = (
            self.db.query(EmailConversation)
            .filter(EmailConversation.lead_id == lead.id, EmailConversation.user_id == self.user_id)
            .order_by(EmailConversation.last_message_at.desc())
            .first()
        )
        if conversation:
            messages = (
                self.db.query(ConversationMessage)
                .filter(ConversationMessage.conversation_id == conversation.id)
                .order_by(ConversationMessage.created_at.asc())
                .limit(10)
                .all()
            )
            for m in messages:
                who = "You" if m.direction == "outbound" else "Lead"
                parts.append(f"{who}: {m.body_text[:120]}")

        emails = EmailOutreachRepository(self.db).list_outreach_emails(self.user_id, limit=200)
        lead_emails = [e for e in emails if e.lead_id == lead.id and e.sent_at]
        for e in lead_emails[-3:]:
            parts.append(f"Sent ({e.follow_up_step}): {e.subject}")

        messages = MessageRepository(self.db).search(
            user_id=self.user_id, lead_id=lead.id, page=1, page_size=5
        )[0]
        for m in messages[:2]:
            parts.append(f"WhatsApp: {m.message_content[:80]}")

        return "; ".join(parts) if parts else "None"

    def generate(
        self,
        lead: Lead,
        *,
        is_follow_up: bool = False,
        follow_up_number: int = 0,
        previous_subject: str | None = None,
    ) -> tuple[str, str]:
        follow_up_hint = ""
        if is_follow_up:
            follow_up_hint = (
                f"This is follow-up #{follow_up_number}. "
                f"Previous subject: {previous_subject or 'n/a'}. "
                "Be brief, add new value, don't repeat the first email."
            )

        prompt = safe_prompt_format(
            OUTREACH_EMAIL_PROMPT,
            sender_profile=self._sender_profile(),
            company_name=lead.company_name or "the business",
            contact_name=lead.contact_name or "there",
            industry=lead.industry or lead.category or "local business",
            website=lead.website or "none",
            location=f"{lead.city or ''}, {lead.country or ''}".strip(", "),
            language_rules=language_rules_for_country(lead.country, lead.city, channel="email"),
            pain_points=self._pain_points(lead),
            buying_intent=f"Score {lead.buying_intent_score or 0}/100 ({lead.intent_tier or 'unknown'})",
            recommended_service=lead.recommended_service or lead.recommended_offer or "web presence improvement",
            previous_interactions=self._previous_interactions(lead),
            follow_up_hint=follow_up_hint,
            first_message_rules=FIRST_MESSAGE_OUTREACH_RULES,
        )

        raw = self.groq._chat(prompt, max_tokens=400, temperature=0.88)
        subject, body = self._parse_response(raw)
        body = sanitize_paid_outreach_message(trim_outreach_message(body, max_chars=600))
        subject = subject.strip()[:120] or f"Quick idea for {lead.company_name}"
        return subject, body

    def _parse_response(self, raw: str) -> tuple[str, str]:
        from app.utils.chat_message_body import extract_subject_and_body

        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        embedded_subj, body = extract_subject_and_body(text)
        if body and (embedded_subj or '"body"' in text.lower()):
            return (embedded_subj or "Following up").strip(), body
        try:
            data = json.loads(text)
            return str(data.get("subject", "")), str(data.get("body", ""))
        except json.JSONDecodeError:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if len(lines) >= 2:
                return lines[0].replace("Subject:", "").strip(), "\n".join(lines[1:])
            return "Following up", text
