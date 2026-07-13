import logging
import re

from app.core.config import get_settings
from app.scraper.metrics import ScrapeMetrics
from app.models.lead import LeadStatus
from app.scrapers.discovery import SearchDiscovery
from app.scrapers.runner import run_business_spider
from app.utils.lead_contacts import sanitize_lead_contacts
from app.utils.scrape_defaults import resolve_scrape_location
from app.utils.scrape_sources import (
    derive_industry_hint,
    has_verified_contact,
    is_quality_business_lead,
    map_no_website_discovery_result,
    map_web_search_result,
    parse_location_parts,
    should_skip_search_url,
)
from app.utils.website_utils import WebsiteFilter

logger = logging.getLogger(__name__)


def _host_key(url: str | None) -> str:
    if not url:
        return ""
    from urllib.parse import urlparse

    host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _discovery_contact_score(item: dict) -> int:
    """Prioritize URLs/snippets that likely contain direct business contacts."""
    text = f"{item.get('title') or ''} {item.get('description') or ''}".lower()
    score = 0
    if "@" in text:
        score += 4
    if re.search(r"\d{7,}", text):
        score += 3
    for hint in ("whatsapp", "contact", "phone", "email", "call us"):
        if hint in text:
            score += 1
    return score


def _prioritize_discovery(discovered: list[dict]) -> list[dict]:
    return sorted(discovered, key=_discovery_contact_score, reverse=True)


def _rank_web_leads(leads: list[dict], crawled_hosts: set[str]) -> list[dict]:
    """Crawled + verified-contact leads first; snippet-only junk last."""

    def sort_key(lead: dict) -> tuple:
        host = _host_key(lead.get("website"))
        from_crawl = host in crawled_hosts
        verified = has_verified_contact(lead)
        score = lead.get("quality_score") or 0
        return (from_crawl, verified, score)

    return sorted(leads, key=sort_key, reverse=True)


class WebSearchService:
    """Internet lead scraping: DDGS search discovery + parallel site crawl."""

    def __init__(self):
        self.discovery = SearchDiscovery()

    def search_leads(
        self,
        keyword: str,
        location: str,
        limit: int,
        search_query: str | None = None,
        metrics: ScrapeMetrics | None = None,
        website_filter: WebsiteFilter = WebsiteFilter.all,
        job_control=None,
        job_id: str | None = None,
    ) -> list[dict]:
        keyword = keyword.strip()
        location = resolve_scrape_location(location)
        industry_hint = derive_industry_hint(keyword, search_query)
        settings = get_settings()
        discovery_limit = max(limit * settings.SCRAPER_DISCOVERY_MULTIPLIER, limit + 10)
        prefer_no_website = website_filter == WebsiteFilter.without_website

        discovered = self.discovery.search(
            keyword=keyword,
            location=location,
            limit=discovery_limit,
            search_query=search_query,
            prefer_no_website=prefer_no_website,
        )
        if not discovered:
            logger.warning(
                "No URLs discovered for query=%s keyword=%s location=%s",
                search_query,
                keyword,
                location,
            )
            return []

        if prefer_no_website:
            no_site_leads = self._leads_from_maps_and_social(discovered, location, limit, industry_hint)
            if no_site_leads:
                if metrics:
                    metrics.inc("leads_parsed", len(no_site_leads))
                return no_site_leads[:limit]

        discovered = _prioritize_discovery(discovered)

        seed_urls: list[str] = []
        seed_titles: dict[str, str] = {}
        seed_descriptions: dict[str, str] = {}
        for item in discovered:
            url = item.get("url") or ""
            if not url or url in seed_titles or should_skip_search_url(url):
                continue
            seed_urls.append(url)
            seed_titles[url] = item.get("title") or ""
            if item.get("description"):
                seed_descriptions[url] = item["description"]

        if metrics:
            metrics.inc("pages_discovered", len(discovered))

        crawl_limit = max(
            int(limit * settings.SCRAPER_CRAWL_SEED_MULTIPLIER),
            limit + 12,
            len(seed_urls),
        )
        scraped = run_business_spider(
            seed_urls,
            seed_titles,
            location,
            limit,
            crawl_seed_limit=crawl_limit,
            seed_descriptions=seed_descriptions,
            industry_hint=industry_hint,
            metrics=metrics,
            job_control=job_control,
            job_id=job_id,
        )
        leads = self._merge_scraped_leads(scraped, location, industry_hint) if scraped else []
        crawled_hosts = {_host_key(lead.get("website")) for lead in leads if lead.get("website")}

        seen = set(crawled_hosts)
        for item in discovered:
            if len(leads) >= limit:
                break
            url = item.get("url") or ""
            host = _host_key(url)
            if not host or host in seen or should_skip_search_url(url):
                continue
            mapped = map_web_search_result(
                {
                    "title": item.get("title"),
                    "url": url,
                    "description": item.get("description"),
                },
                location,
                industry_hint,
                discovery_only=True,
            )
            if mapped:
                leads.append(mapped)
                seen.add(host)

        if not leads:
            return self._fallback_from_discovery(discovered, location, limit, industry_hint)

        ranked = _rank_web_leads(leads, crawled_hosts)
        return ranked[:limit]

    def _leads_from_maps_and_social(
        self,
        discovered: list[dict],
        location: str,
        limit: int,
        industry_hint: str | None,
    ) -> list[dict]:
        leads: list[dict] = []
        seen: set[str] = set()
        for item in discovered:
            if len(leads) >= limit:
                break
            url = item.get("url") or ""
            if not url or url in seen:
                continue
            mapped = map_no_website_discovery_result(item, location, industry_hint)
            if mapped:
                leads.append(mapped)
                seen.add(url)
        return leads

    def _merge_scraped_leads(
        self, scraped: list[dict], location: str, industry_hint: str | None = None
    ) -> list[dict]:
        city, country = parse_location_parts(location)
        leads: list[dict] = []

        for item in scraped:
            company = item.get("company_name") or "Unknown"
            if company == "Unknown":
                continue
            category = item.get("category") or item.get("industry") or industry_hint
            lead = sanitize_lead_contacts(
                {
                    "company_name": company,
                    "contact_name": item.get("contact_name"),
                    "phone": item.get("phone"),
                    "email": item.get("email"),
                    "website": item.get("website"),
                    "linkedin_url": item.get("linkedin_url"),
                    "facebook_url": item.get("facebook_url"),
                    "instagram_url": item.get("instagram_url"),
                    "address": item.get("address"),
                    "postal_code": item.get("postal_code"),
                    "category": category,
                    "city": item.get("city") or city,
                    "country": item.get("country") or country,
                    "industry": category,
                    "notes": item.get("notes"),
                    "source": "web_search",
                    "status": LeadStatus.new,
                    "quality_score": item.get("quality_score"),
                    "quality_tier": item.get("quality_tier"),
                    "whatsapp_ready": item.get("whatsapp_ready"),
                },
                search_location=location,
            )
            if is_quality_business_lead(lead, search_location=location):
                leads.append(lead)

        return leads

    def _fallback_from_discovery(
        self, discovered: list[dict], location: str, limit: int, industry_hint: str | None = None
    ) -> list[dict]:
        leads: list[dict] = []
        for item in discovered:
            mapped = map_web_search_result(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                },
                location,
                industry_hint,
                discovery_only=True,
            )
            if mapped:
                leads.append(mapped)
            if len(leads) >= limit:
                break
        return leads
