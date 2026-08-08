"""Build the sender's real business profile for AI email replies."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.brain import Brain
from app.repositories.brain_repository import BrainRepository
from app.repositories.cv_repository import CVRepository
from app.utils.outreach_tone import resolve_pricing_from_brain


def build_sender_business_context(
    db: Session,
    user_id: int,
    *,
    for_replies: bool = False,
) -> str:
    """Facts the AI may use when answering a customer — never invent beyond this.

    for_replies=True skips the long Brain system_prompt (salesy) so answers stay factual.
    """
    brain: Brain | None = BrainRepository(db).get_by_user(user_id)
    cv = CVRepository(db).get_latest_by_user(user_id)
    parts: list[str] = []

    def _add_list(label: str, values: list | None, limit: int = 10) -> None:
        if not values:
            return
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        if cleaned:
            parts.append(f"{label}: {', '.join(cleaned[:limit])}")

    if brain:
        if brain.name:
            parts.append(f"Business / sender name: {brain.name}")
        if brain.professional_summary:
            parts.append(f"About us: {brain.professional_summary.strip()}")
        _add_list("Services we offer", brain.services)
        _add_list("Skills", brain.skills)
        _add_list("Tools", brain.tools, 8)
        _add_list("Technologies", brain.technologies, 8)
        high, floor, currency = resolve_pricing_from_brain(brain)
        parts.append(
            f"Pricing: opening quote first = {currency} {high:g}; "
            f"minimum acceptable deal = {currency} {floor:g}; "
            f"after opening high, you may negotiate to a fair mid based on the customer, never below floor"
        )
        if brain.projects:
            project_bits: list[str] = []
            for p in brain.projects[:5]:
                if isinstance(p, dict):
                    title = str(p.get("title") or p.get("name") or "").strip()
                    desc = str(p.get("description") or "").strip()
                    if title and desc:
                        project_bits.append(f"{title} — {desc[:120]}")
                    elif title:
                        project_bits.append(title)
                elif str(p).strip():
                    project_bits.append(str(p).strip()[:140])
            if project_bits:
                parts.append("Relevant work / projects: " + "; ".join(project_bits))
        if brain.custom_notes:
            # FAQs / owner notes are valuable for accurate answers
            parts.append(f"Owner notes / FAQs: {brain.custom_notes.strip()[:1200]}")
        if brain.system_prompt and not for_replies:
            parts.append(f"Reply style / business rules: {brain.system_prompt.strip()[:800]}")

    if cv:
        if cv.professional_summary:
            parts.append(f"CV summary: {cv.professional_summary.strip()[:600]}")
        if cv.services_summary:
            parts.append(f"CV services: {cv.services_summary.strip()[:400]}")
        elif cv.services:
            _add_list("CV services", cv.services)
        if cv.skills_summary:
            parts.append(f"CV skills: {cv.skills_summary.strip()[:300]}")
        elif cv.skills:
            _add_list("CV skills", cv.skills)

    if not parts:
        return (
            "Digital services freelancer/agency. "
            "Only answer using conversation context and the pricing rules — "
            "do not invent capabilities, timelines, or guarantees."
        )
    return "\n".join(parts)
