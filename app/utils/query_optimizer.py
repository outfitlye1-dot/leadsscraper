import re

from app.utils.scrape_defaults import (
    DEFAULT_SCRAPE_LOCATION,
    EUROPE_LOCATION_HINTS,
    PAKISTAN_LOCATION_HINTS,
)

CONTACT_HINTS = ("contact", "email", "phone", "whatsapp", "number")
LOCATION_HINTS = EUROPE_LOCATION_HINTS + PAKISTAN_LOCATION_HINTS + (
    "dubai",
    "uae",
    "india",
    "usa",
)


def optimize_search_query_rules(query: str, location: str | None = None) -> dict:
    original = query.strip()
    optimized = re.sub(r"\s+", " ", original)
    tips: list[str] = []
    lower = optimized.lower()
    target_location = (location or "").strip() or DEFAULT_SCRAPE_LOCATION

    if len(optimized.split()) < 3:
        tips.append("Query is short — add business type and location")

    if not any(hint in lower for hint in CONTACT_HINTS):
        optimized = f"{optimized} contact email phone"
        tips.append("Added contact keywords for better leads")

    loc_lower = target_location.lower()
    loc_city = loc_lower.split(",")[0].strip()
    has_location = (
        any(hint in lower for hint in LOCATION_HINTS)
        or " in " in lower
        or (loc_city and loc_city in lower)
        or (loc_lower and loc_lower in lower)
    )
    if not has_location:
        optimized = f"{optimized} {target_location}"
        tips.append(f"Added location: {target_location}")

    optimized = re.sub(r"\s+", " ", optimized).strip()

    niche = _guess_niche(original)
    suggestions = [
        optimized,
        f"{niche} {target_location} contact email",
        f"{niche} {target_location} phone number",
        f"{niche} {target_location} contact whatsapp",
    ]
    unique_suggestions: list[str] = []
    seen: set[str] = set()
    for item in suggestions:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique_suggestions.append(item)

    return {
        "optimized_query": optimized,
        "suggestions": unique_suggestions[:4],
        "tips": ". ".join(tips) if tips else "Query looks good",
        "was_corrected": optimized.lower() != original.lower(),
    }


def _guess_niche(query: str) -> str:
    words = query.strip().split()
    if not words:
        return "business"
    stop = {
        "in",
        "the",
        "a",
        "an",
        "and",
        "or",
        "contact",
        "email",
        "phone",
        "pakistan",
        "london",
        "uk",
        "germany",
        "france",
    }
    kept = [w for w in words[:4] if w.lower() not in stop]
    return " ".join(kept) if kept else "business"
