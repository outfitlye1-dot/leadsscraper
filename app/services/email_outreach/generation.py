"""AI-powered personalized email generation for outreach."""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.models.brain import Brain
from app.models.lead import Lead
from app.repositories.brain_repository import BrainRepository
from app.repositories.cv_repository import CVRepository
from app.services.groq_service import GroqService
from app.utils.outreach_tone import sanitize_paid_outreach_message, trim_outreach_message, CLIENT_PRICING_RULES
from app.utils.prompt_format import safe_prompt_format


OUTREACH_EMAIL_PROMPT = """You are writing a short, human outreach email for a freelancer/agency selling paid digital services to a local small business.

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

RULES:
- Write like a real person, not a marketing template
- Keep body under 90 words
- Paid services only — never offer free audits, trials, or quotes
""" + CLIENT_PRICING_RULES + """
- Reference something specific about their business when possible
- Casual-professional tone
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
        self.brain_repo = BrainRepository(db)
        self.cv_repo = CVRepository(db)

    def _sender_profile(self) -> str:
        brain: Brain | None = self.brain_repo.get_by_user(self.user_id)
        cv = self.cv_repo.get_latest_by_user(self.user_id)
        parts: list[str] = []
        if brain:
            if brain.professional_summary:
                parts.append(brain.professional_summary)
            if brain.services:
                parts.append(f"Services: {', '.join(brain.services[:8])}")
            if brain.skills:
                parts.append(f"Skills: {', '.join(brain.skills[:8])}")
        if cv:
            if cv.professional_summary:
                parts.append(cv.professional_summary)
            if cv.services:
                parts.append(f"Services: {', '.join(cv.services[:8])}")
            if cv.skills:
                parts.append(f"Skills: {', '.join(cv.skills[:8])}")
        return "\n".join(parts) or "Digital services freelancer"

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
            pain_points=self._pain_points(lead),
            buying_intent=f"Score {lead.buying_intent_score or 0}/100 ({lead.intent_tier or 'unknown'})",
            recommended_service=lead.recommended_service or lead.recommended_offer or "web presence improvement",
            previous_interactions=self._previous_interactions(lead),
            follow_up_hint=follow_up_hint,
        )

        raw = self.groq._chat(prompt, max_tokens=400, temperature=0.88)
        subject, body = self._parse_response(raw)
        body = sanitize_paid_outreach_message(trim_outreach_message(body, max_chars=600))
        subject = subject.strip()[:120] or f"Quick idea for {lead.company_name}"
        return subject, body

    def _parse_response(self, raw: str) -> tuple[str, str]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
            return str(data.get("subject", "")), str(data.get("body", ""))
        except json.JSONDecodeError:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if len(lines) >= 2:
                return lines[0].replace("Subject:", "").strip(), "\n".join(lines[1:])
            return "Following up", text
