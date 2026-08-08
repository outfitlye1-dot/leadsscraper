"""Buying intent scoring — likelihood to purchase digital services."""

from __future__ import annotations

import re

from app.utils.scrape_sources import is_listicle_or_bad_title
from app.utils.website_utils import has_real_website

AGENCY_MARKERS = (
    "web agency",
    "marketing agency",
    "digital agency",
    "seo agency",
    "consultant",
    "freelancer",
    "software company",
    "saas",
    "design studio agency",
)


def _is_agency(lead: dict) -> bool:
    text = " ".join(
        str(lead.get(k) or "") for k in ("company_name", "category", "industry", "notes")
    ).lower()
    return any(m in text for m in AGENCY_MARKERS)


def calculate_buying_intent(lead: dict) -> dict:
    score = 40
    reasons: list[str] = []

    website = lead.get("website")
    if not website or not has_real_website(website):
        score += 30
        reasons.append("No real website (+30)")
    elif (lead.get("website_opportunity_score") or 0) >= 50:
        score += 10
        reasons.append("Poor website opportunity (+10)")

    if lead.get("facebook_url") or lead.get("instagram_url"):
        score += 20
        reasons.append("Active social presence (+20)")

    if lead.get("is_running_ads"):
        score += 20
        reasons.append("Running paid ads (+20)")

    reviews = lead.get("reviews_count") or 0
    rating = lead.get("rating") or 0
    if reviews >= 20 or rating >= 4.0:
        score += 15
        reasons.append("Strong Google reviews (+15)")

    meta = dict(lead.get("intelligence_meta") or {})
    if meta.get("recent_review_activity"):
        score += 5

    if (lead.get("google_profile_score") or 0) >= 60 and not has_real_website(website):
        score += 10
        reasons.append("Established business without website (+10)")

    if _is_agency(lead):
        score -= 30
        reasons.append("Agency/competitor (-30)")

    company = lead.get("company_name") or ""
    if is_listicle_or_bad_title(company):
        score -= 20
        reasons.append("Low-quality business name (-20)")

    notes = (lead.get("notes") or "").lower()
    if any(w in notes for w in ("permanently closed", "closed permanently", "out of business")):
        score -= 20
        reasons.append("Possibly closed (-20)")

    if lead.get("_duplicate_risk"):
        score -= 20
        reasons.append("Duplicate risk (-20)")

    score = max(0, min(100, score))
    if score >= 70:
        tier = "hot"
    elif score >= 45:
        tier = "warm"
    else:
        tier = "cold"

    lead["buying_intent_score"] = score
    lead["intent_tier"] = tier
    meta["buying_intent_reasons"] = reasons
    lead["intelligence_meta"] = meta
    return lead
