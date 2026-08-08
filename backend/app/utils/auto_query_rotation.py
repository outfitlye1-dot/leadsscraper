"""Rotate scrape keywords / search queries each auto-scrape round for fresh results."""

from __future__ import annotations

import random
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

# Keep auto queries short — long "contact email phone…" + -site lists make DDGS return empty.
CONTACT_SUFFIXES = (
    "phone",
    "email contact",
    "whatsapp",
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


def _clean_auto_query(keyword: str, location: str, suffix: str = "") -> str:
    """Build a short, location-consistent query DDGS/Bing can actually answer."""
    niche = _strip_contact_words(keyword) or keyword.strip() or "local business"
    loc = location.strip()
    parts = [niche]
    if loc:
        parts.append(loc)
    if suffix:
        parts.append(suffix)
    return " ".join(parts).strip()


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


def lock_auto_scrape_source(base: ScraperStartRequest) -> ScraperStartRequest:
    """Keep the user's selected scrape source — never switch sources silently."""
    source = base.scrape_source
    return base.model_copy(
        update={
            "include_meta_ads": bool(
                base.include_meta_ads and source == ScrapeSourceMode.all
            ),
        }
    )


# Back-compat alias used by older imports/tests
def lock_auto_internet_only(base: ScraperStartRequest) -> ScraperStartRequest:
    return lock_auto_scrape_source(base)


def prepare_auto_scrape_base(
    base: ScraperStartRequest,
    profile: dict | None = None,
) -> ScraperStartRequest:
    """Normalize auto scrape defaults: keep selected source, short query, enrich contacts."""
    source_value = getattr(base.scrape_source, "value", str(base.scrape_source))
    suggestion = (
        suggest_scrape_from_profile_rules(profile, source_value)
        if profile
        else None
    )

    location = base.location.strip() or location_from_brain_notes(profile or {}) or ""
    location = resolve_scrape_location(location)

    keyword = base.keyword.strip() or (suggestion or {}).get("recommended_keyword", "").strip()
    if not keyword and suggestion:
        keyword = (suggestion.get("recommended_keyword") or "").strip()
    if not keyword:
        # Prefer niche from search_query if keyword empty
        raw_q = (base.search_query or "").strip()
        keyword = _strip_contact_words(raw_q) or LOCAL_BUSINESS_KEYWORDS[0]
        # Drop stray location words from keyword if present
        if location:
            for part in re.split(r"[,\s]+", location):
                if len(part) > 2:
                    keyword = re.sub(rf"\b{re.escape(part)}\b", " ", keyword, flags=re.I)
            keyword = re.sub(r"\s+", " ", keyword).strip(" ,.") or LOCAL_BUSINESS_KEYWORDS[0]

    if not location:
        location = DEFAULT_SCRAPE_LOCATION

    search_query = _clean_auto_query(keyword, location)

    # Maps (esp. country multi-city) stays phone-only / no-website — do not force enrich.
    source = base.scrape_source
    maps_only = source == ScrapeSourceMode.google_maps
    return lock_auto_scrape_source(
        base.model_copy(
            update={
                "search_query": search_query,
                "keyword": keyword,
                "location": location,
                "website_filter": (
                    base.website_filter
                    if maps_only
                    else WebsiteFilter.all
                ),
                "enrich_contacts": False if maps_only else True,
            }
        )
    )


def build_auto_scrape_variants(
    base: ScraperStartRequest,
    profile: dict | None = None,
    *,
    max_variants: int = 18,
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

    location = base.location.strip()
    city = location.split(",")[0].strip() if location else ""
    seed_kw = (base.keyword or "").strip() or "local business"
    # Locked keyword: only contact-suffix variants of the same keyword
    if getattr(base, "rotate_keywords", True) is False:
        keywords = [seed_kw]
    else:
        keywords = _related_keywords(base.keyword)

    for kw in keywords[:8]:
        add(
            keyword=kw,
            search_query=_clean_auto_query(kw, location),
            location=location,
        )
        if city and city.lower() != location.lower():
            add(
                keyword=kw,
                search_query=_clean_auto_query(kw, city),
                location=location,
            )
        for suffix in CONTACT_SUFFIXES[:2]:
            add(
                keyword=kw,
                search_query=_clean_auto_query(kw, location, suffix),
                location=location,
            )

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
    return lock_auto_scrape_source(chosen), describe_auto_query(chosen)


def keyword_rotation_pool(
    base_keyword: str,
    profile: dict | None = None,
    *,
    rotate: bool = True,
) -> list[str]:
    """Stable keyword list for country multi-agent auto (rotates each agent/wave)."""
    seed = (base_keyword or "").strip()
    if not rotate:
        return [seed] if seed else ["local business"]
    related = _related_keywords(seed) if seed else list(LOCAL_BUSINESS_KEYWORDS)
    background = _background_keywords(profile)
    pool = _unique_nonempty([seed] + list(related) + background)
    return pool or ["local business"]


def pick_rotated_keyword(pool: list[str], slot: int) -> str:
    if not pool:
        return "local business"
    return pool[max(slot, 0) % len(pool)]


def _background_keywords(profile: dict | None) -> list[str]:
    keywords = list(LOCAL_BUSINESS_KEYWORDS)
    if profile:
        suggestion = suggest_scrape_from_profile_rules(
            profile, ScrapeSourceMode.all.value
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
    """Each round: new keyword, new location, new short search query."""
    keywords = _background_keywords(profile)
    locations = _background_locations(profile)
    i = max(iteration, 1) - 1

    keyword = keywords[(i * 7) % len(keywords)]
    location = locations[(i * 11) % len(locations)]
    suffix = CONTACT_SUFFIXES[(i * 3) % len(CONTACT_SUFFIXES)]
    search_query = _clean_auto_query(keyword, location, suffix)

    data = lock_auto_scrape_source(
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


def pick_fresh_brain_suggestion(
    result: dict,
    *,
    profile: dict | None,
    scrape_source: str,
    current_keyword: str = "",
    current_search_query: str = "",
    location: str = "",
) -> dict:
    """Pick a new random keyword + query, avoiding the user's current values."""
    current_kw = current_keyword.strip().lower()
    current_sq = current_search_query.strip().lower()

    keywords = _unique_nonempty(
        [str(k).strip() for k in (result.get("keyword_suggestions") or []) if str(k).strip()]
        + [str(result.get("recommended_keyword") or "").strip()]
    )
    base_kw = keywords[0] if keywords else "restaurant"
    keywords = _unique_nonempty(keywords + _related_keywords(base_kw) + list(LOCAL_BUSINESS_KEYWORDS))

    loc = resolve_scrape_location(location.strip() or (result.get("recommended_location") or ""))
    if not loc:
        loc = DEFAULT_SCRAPE_LOCATION

    candidates: list[tuple[str, str]] = []
    suffixes = CONTACT_SUFFIXES if scrape_source != "google_maps" else ("", "phone")

    for kw in keywords[:16]:
        for suffix in suffixes:
            candidates.append((kw, _clean_auto_query(kw, loc, suffix)))

    for sq in result.get("search_queries") or []:
        text = str(sq).strip()
        if not text:
            continue
        kw = _strip_contact_words(text) or base_kw
        candidates.append((kw, text))

    seen: set[tuple[str, str]] = set()
    fresh: list[tuple[str, str]] = []
    for kw, sq in candidates:
        key = (kw.lower(), sq.lower())
        if key in seen:
            continue
        seen.add(key)
        if current_kw and kw.lower() == current_kw:
            continue
        if current_sq and sq.lower() == current_sq:
            continue
        fresh.append((kw, sq))

    pool = fresh if fresh else candidates
    if not pool:
        pool = [(base_kw, _clean_auto_query(base_kw, loc))]

    kw, sq = random.choice(pool)
    updated = dict(result)
    updated["recommended_keyword"] = kw
    updated["recommended_search_query"] = sq
    return updated

