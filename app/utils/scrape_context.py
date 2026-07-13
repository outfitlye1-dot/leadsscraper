"""Tag and match leads to scrape queries (background cache + manual scrape)."""

from __future__ import annotations

from app.schemas.common import ScraperStartRequest
from app.utils.scrape_defaults import normalize_location_alias, resolve_scrape_location
from app.utils.website_utils import WebsiteFilter, has_real_website


def scrape_request_signature(data: ScraperStartRequest) -> str:
    loc = normalize_location_alias(resolve_scrape_location((data.location or "").strip()))
    return "|".join(
        [
            data.scrape_source.value,
            data.website_filter.value,
            (data.keyword or "").strip().lower(),
            loc.lower(),
            ((data.search_query or "").strip().lower()),
        ]
    )


def tag_leads_with_scrape_context(
    leads: list[dict],
    data: ScraperStartRequest,
    *,
    background: bool = False,
) -> list[dict]:
    if not leads:
        return leads
    signature = scrape_request_signature(data)
    ctx = {
        "signature": signature,
        "keyword": (data.keyword or "").strip(),
        "location": (data.location or "").strip(),
        "search_query": (data.search_query or "").strip(),
        "scrape_source": data.scrape_source.value,
        "website_filter": data.website_filter.value,
        "background": background,
    }
    tagged: list[dict] = []
    for lead in leads:
        row = dict(lead)
        meta = dict(row.get("intelligence_meta") or {})
        meta["scrape_context"] = ctx
        row["intelligence_meta"] = meta
        tagged.append(row)
    return tagged


def _location_matches(lead, location: str) -> bool:
    loc = location.strip().lower()
    if not loc:
        return True
    city = loc.split(",")[0].strip()
    country = loc.split(",")[-1].strip() if "," in loc else ""
    lead_city = (getattr(lead, "city", None) or "").lower()
    lead_country = (getattr(lead, "country", None) or "").lower()
    notes = (getattr(lead, "notes", None) or "").lower()
    if city and city in lead_city:
        return True
    if country and country in lead_country:
        return True
    if city and city in notes:
        return True
    if loc in notes:
        return True
    return city in loc and not lead_city and not lead_country


def _keyword_matches(lead, keyword: str, search_query: str) -> bool:
    kw = keyword.strip().lower()
    sq = search_query.strip().lower()
    if not kw and not sq:
        return True
    blob = " ".join(
        filter(
            None,
            [
                getattr(lead, "company_name", None),
                getattr(lead, "category", None),
                getattr(lead, "industry", None),
                getattr(lead, "notes", None),
            ],
        )
    ).lower()
    meta = getattr(lead, "intelligence_meta", None) or {}
    ctx = meta.get("scrape_context") or {}
    ctx_kw = (ctx.get("keyword") or "").lower()
    ctx_sq = (ctx.get("search_query") or "").lower()
    if kw and (kw in blob or kw in ctx_kw or kw in ctx_sq):
        return True
    if sq:
        for token in sq.split():
            if len(token) > 3 and token in blob:
                return True
        if sq in ctx_sq:
            return True
    return not kw and not sq


def _website_filter_matches(lead, website_filter: WebsiteFilter) -> bool:
    if website_filter == WebsiteFilter.all:
        return True
    has_site = has_real_website(getattr(lead, "website", None))
    if website_filter == WebsiteFilter.without_website:
        return not has_site
    return has_site


def lead_matches_scrape_request(lead, data: ScraperStartRequest) -> bool:
    meta = getattr(lead, "intelligence_meta", None) or {}
    ctx = meta.get("scrape_context") or {}
    if ctx.get("signature") == scrape_request_signature(data):
        return True
    if ctx.get("scrape_source") and ctx.get("scrape_source") != data.scrape_source.value:
        return False
    if not _website_filter_matches(lead, data.website_filter):
        return False
    if not _location_matches(lead, data.location or ""):
        return False
    return _keyword_matches(lead, data.keyword or "", data.search_query or "")


def is_background_lead(lead) -> bool:
    meta = getattr(lead, "intelligence_meta", None) or {}
    if not isinstance(meta, dict):
        return False
    ctx = meta.get("scrape_context") or {}
    return bool(ctx.get("background"))
