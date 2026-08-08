"""Lead data quality scoring: High / Medium / Low."""

from __future__ import annotations

from app.utils.contact_utils import is_valid_email, is_whatsapp_ready
from app.utils.website_utils import has_real_website

QUALITY_HIGH = "high"
QUALITY_MEDIUM = "medium"
QUALITY_LOW = "low"


def score_lead_quality(lead: dict) -> tuple[int, str]:
    """
    Score 0-100 and tier.
    High: company + verified contact + website context
    Medium: company + one verified contact or website
    Low: minimal usable record
    """
    score = 0
    country = lead.get("country")

    if lead.get("company_name"):
        score += 15
    if lead.get("source") == "meta_ads":
        score += 10
    if has_real_website(lead.get("website")):
        score += 15
    if lead.get("email") and is_valid_email(lead.get("email")):
        score += 25
    if lead.get("phone"):
        score += 15
        if is_whatsapp_ready(lead.get("phone"), country):
            score += 15
    if lead.get("address"):
        score += 5
    if lead.get("city") or lead.get("country"):
        score += 5
    if lead.get("contact_name"):
        score += 5
    for social in ("linkedin_url", "facebook_url", "instagram_url"):
        if lead.get(social):
            score += 3

    score = min(score, 100)

    has_contact = bool(
        (lead.get("email") and is_valid_email(lead.get("email")))
        or (lead.get("phone") and is_whatsapp_ready(lead.get("phone"), country))
    )
    has_website = has_real_website(lead.get("website"))

    if score >= 70 and has_contact and lead.get("company_name"):
        tier = QUALITY_HIGH
    elif score >= 40 and (has_contact or has_website):
        tier = QUALITY_MEDIUM
    else:
        tier = QUALITY_LOW

    return score, tier


def apply_quality_to_lead(lead: dict) -> dict:
    score, tier = score_lead_quality(lead)
    enriched = dict(lead)
    enriched["quality_score"] = score
    enriched["quality_tier"] = tier
    enriched["whatsapp_ready"] = bool(
        lead.get("phone") and is_whatsapp_ready(lead.get("phone"), lead.get("country"))
    )
    return enriched
