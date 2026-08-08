"""Niche-specific pain points, opportunity signals, and recommended services."""

from __future__ import annotations

import re

NICHE_RULES: dict[str, dict] = {
    "restaurant": {
        "keywords": ("restaurant", "cafe", "café", "bistro", "diner", "pizzeria", "bakery", "food"),
        "pain_points": [
            "No online ordering",
            "No reservation/booking system",
            "No digital menu",
            "Poor mobile experience",
        ],
        "opportunity_signals": ("menu", "order", "reservation", "delivery", "table booking"),
        "recommended_service": "Restaurant website + online ordering & reservations",
    },
    "salon": {
        "keywords": ("salon", "barber", "spa", "beauty", "hair", "nails", "cosmetic"),
        "pain_points": [
            "No online booking",
            "No service/pricing page",
            "Weak Instagram presence",
            "No portfolio/gallery",
        ],
        "opportunity_signals": ("book", "appointment", "services", "pricing", "gallery"),
        "recommended_service": "Salon website + online booking system",
    },
    "clinic": {
        "keywords": ("clinic", "dental", "dentist", "doctor", "medical", "physio", "health"),
        "pain_points": [
            "No patient booking",
            "Missing trust signals",
            "No service descriptions",
            "Poor accessibility",
        ],
        "opportunity_signals": ("appointment", "patient", "treatment", "consultation"),
        "recommended_service": "Clinic website + appointment booking",
    },
    "gym": {
        "keywords": ("gym", "fitness", "yoga", "crossfit", "training", "pilates"),
        "pain_points": [
            "No class schedule online",
            "No membership signup",
            "No trainer profiles",
        ],
        "opportunity_signals": ("membership", "class", "schedule", "trainer", "trial"),
        "recommended_service": "Gym website + membership & class booking",
    },
    "hotel": {
        "keywords": ("hotel", "motel", "guesthouse", "resort", "hostel", "lodging", "bnb"),
        "pain_points": [
            "No direct booking",
            "Depends on OTAs only",
            "No room gallery",
            "Missing amenities page",
        ],
        "opportunity_signals": ("book", "room", "reservation", "amenities", "check-in"),
        "recommended_service": "Hotel website + direct booking engine",
    },
    "real_estate": {
        "keywords": ("real estate", "realtor", "property", "estate agent", "realty"),
        "pain_points": [
            "No property listings",
            "No lead capture forms",
            "Weak local SEO",
        ],
        "opportunity_signals": ("listing", "property", "mortgage", "valuation", "viewing"),
        "recommended_service": "Real estate website + property listings & lead forms",
    },
}

DEFAULT_NICHE = {
    "pain_points": [
        "No professional website",
        "Missing contact capture",
        "Weak online presence",
    ],
    "opportunity_signals": ("contact", "services", "about", "pricing"),
    "recommended_service": "Professional business website + lead generation",
}


def detect_niche(lead: dict) -> str:
    text = " ".join(
        str(lead.get(k) or "")
        for k in ("company_name", "category", "industry", "notes")
    ).lower()
    for niche_key, rule in NICHE_RULES.items():
        if any(kw in text for kw in rule["keywords"]):
            return niche_key
    return "general"


def apply_niche_intelligence(lead: dict) -> dict:
    niche_key = detect_niche(lead)
    rule = NICHE_RULES.get(niche_key, DEFAULT_NICHE)
    problems = list(lead.get("website_problems") or [])
    meta = dict(lead.get("intelligence_meta") or {})
    crawl_text = " ".join(
        str(meta.get(k, "")) for k in ("crawl_services", "crawl_description", "pages_crawled")
    ).lower()

    niche_pains = []
    for pain in rule["pain_points"]:
        signal_words = rule.get("opportunity_signals", ())
        if not any(sig in crawl_text for sig in signal_words):
            niche_pains.append(pain)

    if not lead.get("website") or meta.get("no_real_website"):
        if "No professional website" not in niche_pains:
            niche_pains.insert(0, "No professional website")

    merged_problems = list(dict.fromkeys(problems + niche_pains))[:12]
    lead["niche_key"] = niche_key
    lead["recommended_service"] = rule["recommended_service"]
    lead["website_problems"] = merged_problems
    meta["niche_pain_points"] = niche_pains
    lead["intelligence_meta"] = meta
    return lead
