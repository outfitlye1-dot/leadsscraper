"""Rule-based scrape suggestions from CV/brain profile when AI is unavailable."""

from __future__ import annotations

from app.utils.scrape_defaults import (
    DEFAULT_SCRAPE_LOCATION,
    EUROPE_LOCATION_SUGGESTIONS,
)

# Local brick-and-mortar businesses that typically BUY web/digital services (not agencies).
_LOCAL_BUYER_KEYWORDS: dict[str, list[str]] = {
    "web": ["restaurant", "beauty salon", "dental clinic", "coffee shop", "plumber"],
    "design": ["restaurant", "hair salon", "boutique shop", "bakery", "fitness gym"],
    "seo": ["dental practice", "local restaurant", "real estate agent", "law firm", "auto repair"],
    "marketing": ["retail shop", "spa salon", "veterinary clinic", "florist", "cafe"],
    "social": ["restaurant", "salon", "gym", "clothing store", "pet groomer"],
    "default": ["restaurant", "beauty salon", "dental clinic", "local shop", "gym"],
}


def _profile_text(profile: dict) -> str:
    parts: list[str] = []
    for key in ("services", "skills", "professional_summary", "custom_notes"):
        val = profile.get(key)
        if isinstance(val, list):
            parts.extend(str(v) for v in val)
        elif val:
            parts.append(str(val))
    return " ".join(parts).lower()


def _local_keywords_for_profile(profile: dict) -> list[str]:
    text = _profile_text(profile)
    for key, keywords in _LOCAL_BUYER_KEYWORDS.items():
        if key == "default":
            continue
        if key in text:
            return keywords
    return _LOCAL_BUYER_KEYWORDS["default"]


def _location_from_notes(profile: dict) -> str | None:
    notes = (profile.get("custom_notes") or "").strip()
    if not notes:
        return None
    for line in notes.replace("\n", ",").split(","):
        chunk = line.strip()
        if "," in chunk and len(chunk) > 4:
            return chunk
    return None


def location_from_brain_notes(profile: dict) -> str | None:
    """User-written city in Brain custom_notes (not AI-suggested)."""
    return _location_from_notes(profile)


def suggest_scrape_from_profile_rules(profile: dict, scrape_source: str = "all") -> dict:
    name = profile.get("name") or "your profile"
    keywords = _local_keywords_for_profile(profile)
    locations = EUROPE_LOCATION_SUGGESTIONS[:4]
    custom_loc = _location_from_notes(profile)
    if custom_loc:
        locations = [custom_loc, *locations[:3]]

    primary_kw = keywords[0]
    primary_loc = locations[0]

    search_queries = [
        f"{kw} {locations[i % len(locations)].split(',')[0]} contact phone email whatsapp"
        for i, kw in enumerate(keywords[:4])
    ]
    if not search_queries:
        search_queries = [
            f"{primary_kw} {primary_loc} contact phone email",
        ]

    tips = (
        f"Based on {name}'s profile, target local brick-and-mortar businesses "
        f"(e.g. {', '.join(keywords[:3])}) in {primary_loc.split(',')[-1].strip()} — "
        "shops and services with a physical location, often without a professional website. "
        "Avoid agencies, SaaS, or online-only companies."
    )

    if scrape_source == "google_maps":
        search_queries = search_queries[:2]

    return {
        "recommended_keyword": primary_kw,
        "recommended_location": primary_loc,
        "recommended_search_query": search_queries[0],
        "keyword_suggestions": keywords[:4],
        "location_suggestions": locations[:4],
        "search_queries": search_queries[:5],
        "strategy_tips": tips,
        "profile_name": profile.get("name"),
        "has_profile": True,
    }
