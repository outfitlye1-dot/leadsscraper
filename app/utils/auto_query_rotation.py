"""Rotate scrape keywords / search queries each auto-scrape round for fresh results."""

from __future__ import annotations

import re

from app.schemas.common import ScraperStartRequest
from app.utils.scrape_defaults import (
    DEFAULT_SCRAPE_LOCATION,
    EUROPE_LOCATION_SUGGESTIONS,
    resolve_scrape_location,
)
from app.utils.scrape_sources import ScrapeSourceMode
from app.utils.scrape_suggest import location_from_brain_notes, suggest_scrape_from_profile_rules
from app.utils.website_utils import WebsiteFilter

CONTACT_SUFFIXES = (
    "contact email phone",
    "whatsapp phone number",
    "business email contact",
    "phone number email",
    "contact us email whatsapp",
)

LOCAL_BUSINESS_KEYWORDS = (
    "restaurant",
    "beauty salon",
    "dental clinic",
    "coffee shop",
    "plumber",
    "electrician",
    "gym",
    "bakery",
    "florist",
    "barber shop",
    "auto repair",
    "veterinary clinic",
    "boutique",
    "spa",
    "cafe",
)

KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    "restaurant": ("restaurant", "cafe", "coffee shop", "bistro", "pizzeria", "takeaway"),
    "salon": ("beauty salon", "hair salon", "barber shop", "nail salon", "spa"),
    "clinic": ("dental clinic", "medical clinic", "veterinary clinic", "physiotherapy clinic"),
    "shop": ("boutique", "retail shop", "local shop", "clothing store", "gift shop"),
    "gym": ("gym", "fitness center", "yoga studio", "personal trainer"),
    "web": ("restaurant", "beauty salon", "dental clinic", "local shop", "plumber"),
    "design": ("restaurant", "salon", "boutique", "bakery", "florist"),
}


def _unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = re.sub(r"\s+", " ", (item or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _strip_contact_words(text: str) -> str:
    cleaned = re.sub(
        r"\b(contact|email|phone|whatsapp|number|business|website|company|near me)\b",
        " ",
        text,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", cleaned).strip(" ,.")


def _related_keywords(base: str) -> list[str]:
    base_lower = base.strip().lower()
    if not base_lower:
        return list(LOCAL_BUSINESS_KEYWORDS[:10])

    for key, group in KEYWORD_GROUPS.items():
        if key in base_lower or base_lower in group:
            return list(group)

    alts = [base.strip()]
    for item in LOCAL_BUSINESS_KEYWORDS:
        if item.lower() != base_lower:
            alts.append(item)
    return alts[:12]


def _variant_key(data: ScraperStartRequest) -> str:
    parts = [
        data.scrape_source.value,
        data.keyword.strip().lower(),
        (data.search_query or "").strip().lower(),
        data.location.strip().lower(),
    ]
    return "|".join(parts)


def describe_auto_query(data: ScraperStartRequest) -> str:
    if data.search_query and data.search_query.strip():
        text = data.search_query.strip()
        return text if len(text) <= 90 else f"{text[:87]}..."
    if data.keyword.strip():
        return f"{data.keyword.strip()} — {data.location.strip() or 'location'}"
    return "scrape query"


def lock_auto_internet_only(base: ScraperStartRequest) -> ScraperStartRequest:
    """Hard lock: auto scraper must never use Maps, Apify, or Meta."""
    return base.model_copy(
        update={
            "scrape_source": ScrapeSourceMode.google_search,
            "include_meta_ads": False,
        }
    )


def prepare_auto_scrape_base(
    base: ScraperStartRequest,
    profile: dict | None = None,
) -> ScraperStartRequest:
    """Auto scraper always runs Internet (google_search) only."""
    suggestion = (
        suggest_scrape_from_profile_rules(profile, ScrapeSourceMode.google_search.value)
        if profile
        else None
    )

    location = base.location.strip() or location_from_brain_notes(profile or {}) or ""
    location = resolve_scrape_location(location)

    keyword = base.keyword.strip() or (suggestion or {}).get("recommended_keyword", "").strip()
    search_query = (base.search_query or "").strip()

    if not search_query and suggestion:
        search_query = (suggestion.get("recommended_search_query") or "").strip()
        if not search_query:
            queries = suggestion.get("search_queries") or []
            if queries:
                search_query = queries[0].strip()
                if location and location.lower() not in search_query.lower():
                    city = location.split(",")[0].strip()
                    search_query = f"{search_query} {city} {location.split(',')[-1].strip()}".strip()

    if not search_query:
        if keyword and location:
            search_query = f"{keyword} {location} contact email phone"
        elif keyword:
            search_query = f"{keyword} contact email phone"
        elif location:
            search_query = f"local business {location} contact email phone whatsapp"
        else:
            search_query = f"local business {DEFAULT_SCRAPE_LOCATION} contact email phone"

    if not keyword and suggestion:
        keyword = (suggestion.get("recommended_keyword") or "").strip()

    if not keyword:
        keyword = LOCAL_BUSINESS_KEYWORDS[0]

    if not location:
        location = DEFAULT_SCRAPE_LOCATION

    return lock_auto_internet_only(
        base.model_copy(
            update={
                "search_query": search_query,
                "keyword": keyword,
                "location": location,
                "website_filter": WebsiteFilter.all,
                "enrich_contacts": True,
            }
        )
    )


def build_auto_scrape_variants(
    base: ScraperStartRequest,
    profile: dict | None = None,
    *,
    max_variants: int = 30,
) -> list[ScraperStartRequest]:
    base = prepare_auto_scrape_base(base, profile)
    variants: list[ScraperStartRequest] = []
    seen: set[str] = set()

    def add(**updates: object) -> None:
        payload = base.model_copy(update=updates)
        key = _variant_key(payload)
        if key in seen:
            return
        seen.add(key)
        variants.append(payload)

    suggestion = (
        suggest_scrape_from_profile_rules(profile, ScrapeSourceMode.google_search.value)
        if profile
        else None
    )
    location = base.location.strip()

    search_queries = _unique_nonempty(
        [
            base.search_query.strip(),
            *(suggestion or {}).get("search_queries", []),
        ]
    )
    if base.keyword and location:
        search_queries = _unique_nonempty(
            [
                *search_queries,
                f"{base.keyword} {location} contact email phone",
                f"{base.keyword} {location} whatsapp number",
            ]
        )

    for query in search_queries:
        add(search_query=query)
        niche = _strip_contact_words(query)
        if not niche:
            continue
        for suffix in CONTACT_SUFFIXES:
            sq = f"{niche} {suffix}".strip()
            if location and location.lower() not in sq.lower():
                sq = f"{sq} {location}".strip()
            add(search_query=sq)

    if not variants:
        variants.append(base)

    return variants[:max_variants]


def pick_auto_scrape_request(
    base: ScraperStartRequest,
    profile: dict | None,
    iteration: int,
) -> tuple[ScraperStartRequest, str]:
    pool = build_auto_scrape_variants(base, profile)
    chosen = pool[(max(iteration, 1) - 1) % len(pool)]
    return lock_auto_internet_only(chosen), describe_auto_query(chosen)


def _background_keywords(profile: dict | None) -> list[str]:
    keywords = list(LOCAL_BUSINESS_KEYWORDS)
    if profile:
        suggestion = suggest_scrape_from_profile_rules(
            profile, ScrapeSourceMode.google_search.value
        )
        if suggestion:
            kw = (suggestion.get("recommended_keyword") or "").strip()
            if kw:
                keywords.insert(0, kw)
        for svc in profile.get("services") or []:
            text = str(svc).strip()
            if text:
                keywords.append(text)
    return _unique_nonempty(keywords)


def _background_locations(profile: dict | None) -> list[str]:
    locations = [resolve_scrape_location(loc) for loc in EUROPE_LOCATION_SUGGESTIONS]
    brain_loc = location_from_brain_notes(profile or {})
    if brain_loc:
        resolved = resolve_scrape_location(brain_loc)
        if resolved not in locations:
            locations.insert(0, resolved)
    return _unique_nonempty(locations)


def pick_background_scrape_request(
    base: ScraperStartRequest,
    profile: dict | None,
    iteration: int,
) -> tuple[ScraperStartRequest, str]:
    """Each round: new keyword, new location, new search query (background scraper)."""
    keywords = _background_keywords(profile)
    locations = _background_locations(profile)
    i = max(iteration, 1) - 1

    keyword = keywords[(i * 7) % len(keywords)]
    location = locations[(i * 11) % len(locations)]
    suffix = CONTACT_SUFFIXES[(i * 3) % len(CONTACT_SUFFIXES)]
    search_query = f"{keyword} {location} {suffix}".strip()

    data = lock_auto_internet_only(
        base.model_copy(
            update={
                "keyword": keyword,
                "location": location,
                "search_query": search_query,
                "website_filter": WebsiteFilter.all,
                "enrich_contacts": True,
            }
        )
    )
    return data, f"{keyword} — {location}"
