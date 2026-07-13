"""AI/rule-based lead qualification after scraping."""

from __future__ import annotations

from app.services.intelligence.niche_intelligence import detect_niche, NICHE_RULES, DEFAULT_NICHE


def qualify_lead_rules(lead: dict) -> dict:
    """Rule-based qualification — always available without Groq."""
    intent = lead.get("buying_intent_score") or 0
    tier = lead.get("intent_tier") or "cold"
    niche = lead.get("niche_key") or detect_niche(lead)
    service = lead.get("recommended_service") or NICHE_RULES.get(niche, DEFAULT_NICHE)["recommended_service"]

    problems = lead.get("website_problems") or []
    company = lead.get("company_name") or "Business"

    if tier == "hot" and (lead.get("phone_verified") or lead.get("email_verified")):
        qualification = "qualified"
        reason = (
            f"{company} is a high-intent {niche.replace('_', ' ')} prospect "
            f"(score {intent}/100). "
            f"Key gaps: {', '.join(problems[:3]) or 'weak digital presence'}."
        )
    elif tier == "warm":
        qualification = "review"
        reason = (
            f"{company} shows moderate buying signals ({intent}/100). "
            "Worth outreach with a tailored offer."
        )
    else:
        qualification = "low"
        reason = f"{company} has limited buying signals ({intent}/100) for digital services."

    if lead.get("is_running_ads"):
        reason += " They are actively spending on ads — strong web/landing page opportunity."

    lead["ai_qualification"] = qualification
    lead["recommended_offer"] = service
    lead["qualification_reason"] = reason
    return lead


def qualify_lead_with_ai(lead: dict, groq_service, cv_profile: dict | None = None) -> dict:
    """Optional Groq enhancement; falls back to rules on failure."""
    qualify_lead_rules(lead)
    if groq_service is None:
        return lead
    try:
        prompt = (
            "You qualify local business leads for digital service sales.\n"
            f"Lead JSON: {lead}\n"
            "Reply JSON only: {\"qualification\":\"qualified|review|low\","
            "\"recommended_offer\":\"...\",\"qualification_reason\":\"...\"}"
        )
        result = groq_service._chat(prompt, max_tokens=200, temperature=0.3)
        import json
        import re

        match = re.search(r"\{.*\}", result, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            if parsed.get("qualification"):
                lead["ai_qualification"] = str(parsed["qualification"])[:20]
            if parsed.get("recommended_offer"):
                lead["recommended_offer"] = str(parsed["recommended_offer"])[:500]
            if parsed.get("qualification_reason"):
                lead["qualification_reason"] = str(parsed["qualification_reason"])[:1000]
    except Exception:
        pass
    return lead
