import logging
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from app.core.config import get_settings
from app.scraper.metrics import ScrapeMetrics
from app.models.lead import LeadStatus
from app.scrapers.crawler_core import scrape_business_site
from app.scrapers.discovery import SearchDiscovery
from app.scrapers.fetcher import PageFetcher
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
    """Internet lead scraping: multi-engine discovery + parallel site crawl."""

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
        max_seconds: float | None = None,
        light: bool = False,
    ) -> list[dict]:
        keyword = keyword.strip()
        location = resolve_scrape_location(location)
        industry_hint = derive_industry_hint(keyword, search_query)
        settings = get_settings()
        if light:
            discovery_limit = min(max(limit + 4, limit), 10)
        else:
            discovery_limit = min(
                max(limit * settings.SCRAPER_DISCOVERY_MULTIPLIER, limit + 8),
                limit * 2 + 12,
                36,
            )
        prefer_no_website = website_filter == WebsiteFilter.without_website
        use_pipeline = settings.SCRAPER_INTERNET_PIPELINE and not light
        budget = (
            float(max_seconds)
            if max_seconds is not None and max_seconds > 0
            else max(30.0, float(settings.SCRAPER_INTERNET_MAX_SECONDS or 60.0))
        )
        deadline = time.monotonic() + budget
        # Prevent Windows DNS / connect hangs that ignore requests timeout
        prev_sock_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(min(5.0 if light else 8.0, float(settings.SCRAPER_TIMEOUT) + 2.0))

        def timed_job_control() -> bool:
            if time.monotonic() >= deadline:
                return True
            return bool(job_control and job_control())

        try:
            if use_pipeline:
                return self._search_leads_pipeline(
                    keyword=keyword,
                    location=location,
                    limit=limit,
                    discovery_limit=discovery_limit,
                    search_query=search_query,
                    prefer_no_website=prefer_no_website,
                    industry_hint=industry_hint,
                    metrics=metrics,
                    job_control=timed_job_control,
                    job_id=job_id,
                    deadline=deadline,
                )

            discovered = self.discovery.search(
                keyword=keyword,
                location=location,
                limit=discovery_limit,
                search_query=search_query,
                prefer_no_website=prefer_no_website,
                deadline=deadline,
                metrics=metrics,
            )
            return self._finish_from_discovered(
                discovered,
                location=location,
                limit=limit,
                prefer_no_website=prefer_no_website,
                industry_hint=industry_hint,
                metrics=metrics,
                job_control=timed_job_control,
                job_id=job_id,
            )
        finally:
            socket.setdefaulttimeout(prev_sock_timeout)

    def _search_leads_pipeline(
        self,
        *,
        keyword: str,
        location: str,
        limit: int,
        discovery_limit: int,
        search_query: str | None,
        prefer_no_website: bool,
        industry_hint: str | None,
        metrics: ScrapeMetrics | None,
        job_control,
        job_id: str | None,
        deadline: float | None = None,
    ) -> list[dict]:
        settings = get_settings()
        # Sequential discover → short crawl. Overlap hung Windows workers forever.
        logger.info(
            "Internet scrape: discover then crawl (target=%s · deadline=%ss · fast=%s)",
            limit,
            int(settings.SCRAPER_INTERNET_MAX_SECONDS or 60),
            settings.SCRAPER_FAST_MODE,
        )

        discovered = self.discovery.search(
            keyword=keyword,
            location=location,
            limit=discovery_limit,
            search_query=search_query,
            prefer_no_website=prefer_no_website,
            on_batch=None,
            deadline=deadline,
            metrics=metrics,
        )

        if not discovered:
            logger.warning(
                "No URLs discovered for query=%s keyword=%s location=%s",
                search_query,
                keyword,
                location,
            )
            return []

        if metrics:
            metrics.inc("pages_discovered", len(discovered))

        maps_social_leads: list[dict] = []
        if prefer_no_website:
            maps_social_leads = self._leads_from_maps_and_social(
                discovered, location, limit, industry_hint
            )

        if deadline is not None and time.monotonic() >= deadline:
            logger.info("Internet deadline during discovery — returning search snippets only")
            return self._blend_discovery_fills(
                discovered,
                list(maps_social_leads),
                set(),
                location=location,
                limit=limit,
                prefer_no_website=prefer_no_website,
                industry_hint=industry_hint,
                maps_social_leads=maps_social_leads,
            )

        crawl_limit = min(
            max(int(limit * settings.SCRAPER_CRAWL_SEED_MULTIPLIER), limit + 4),
            limit * 2 + 4,
            16,
        )
        remaining = 20.0
        if deadline is not None:
            remaining = max(2.0, min(25.0, deadline - time.monotonic()))

        seed_items = _prioritize_discovery(
            [
                item
                for item in discovered
                if (item.get("url") or "")
                and not should_skip_search_url(item["url"], allow_maps_social=False)
            ]
        )[:crawl_limit]

        crawled: list[dict] = []
        # Short timed enrich — Windows DNS can ignore socket timeouts and hang forever.
        if seed_items and remaining >= 3 and not (job_control and job_control()):
            crawl_budget = min(remaining, 12.0 if settings.SCRAPER_FAST_MODE else 18.0)
            seeds = seed_items[: max(4, min(6, crawl_limit))]
            enrich_ex = ThreadPoolExecutor(max_workers=1)
            try:
                enrich_fut = enrich_ex.submit(
                    self._fast_http_enrich,
                    seeds,
                    location=location,
                    industry_hint=industry_hint,
                    limit=limit,
                    budget_seconds=crawl_budget,
                    job_control=job_control,
                    metrics=metrics,
                )
                try:
                    crawled = enrich_fut.result(timeout=crawl_budget + 3.0) or []
                except TimeoutError:
                    logger.warning(
                        "Internet enrich timed out after %.0fs — using discovery snippets",
                        crawl_budget + 3.0,
                    )
                    crawled = []
            finally:
                enrich_ex.shutdown(wait=False, cancel_futures=True)
        else:
            logger.info(
                "Internet finish: %s discovery URLs → snippet leads (no crawl budget)",
                len(discovered),
            )

        leads: list[dict] = list(maps_social_leads)
        crawled_hosts = {_host_key(lead.get("website")) for lead in crawled if lead.get("website")}
        leads.extend(crawled)

        return self._blend_discovery_fills(
            discovered,
            leads,
            crawled_hosts,
            location=location,
            limit=limit,
            prefer_no_website=prefer_no_website,
            industry_hint=industry_hint,
            maps_social_leads=maps_social_leads,
        )

    def _finish_from_discovered(
        self,
        discovered: list[dict],
        *,
        location: str,
        limit: int,
        prefer_no_website: bool,
        industry_hint: str | None,
        metrics: ScrapeMetrics | None,
        job_control,
        job_id: str | None,
    ) -> list[dict]:
        if not discovered:
            logger.warning("No URLs discovered for keyword/location scrape")
            return []

        settings = get_settings()
        maps_social_leads: list[dict] = []
        if prefer_no_website:
            maps_social_leads = self._leads_from_maps_and_social(
                discovered, location, limit, industry_hint
            )

        discovered = _prioritize_discovery(discovered)

        seed_urls: list[str] = []
        seed_titles: dict[str, str] = {}
        seed_descriptions: dict[str, str] = {}
        for item in discovered:
            url = item.get("url") or ""
            if not url or url in seed_titles:
                continue
            if should_skip_search_url(url, allow_maps_social=False):
                continue
            seed_urls.append(url)
            seed_titles[url] = item.get("title") or ""
            if item.get("description"):
                seed_descriptions[url] = item["description"]

        if metrics:
            metrics.inc("pages_discovered", len(discovered))

        crawl_limit = min(
            max(int(limit * settings.SCRAPER_CRAWL_SEED_MULTIPLIER), limit + 6),
            limit * 2 + 8,
            28,
        )
        logger.info(
            "Internet crawl: %s seed URLs · target=%s · seed_cap=%s",
            len(seed_urls),
            limit,
            crawl_limit,
        )

        leads: list[dict] = list(maps_social_leads)
        crawled_hosts: set[str] = set()

        if seed_urls:
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
            crawled = self._merge_scraped_leads(scraped, location, industry_hint) if scraped else []
            crawled_hosts = {_host_key(lead.get("website")) for lead in crawled if lead.get("website")}
            leads.extend(crawled)

        return self._blend_discovery_fills(
            discovered,
            leads,
            crawled_hosts,
            location=location,
            limit=limit,
            prefer_no_website=prefer_no_website,
            industry_hint=industry_hint,
            maps_social_leads=maps_social_leads,
        )

    def _blend_discovery_fills(
        self,
        discovered: list[dict],
        leads: list[dict],
        crawled_hosts: set[str],
        *,
        location: str,
        limit: int,
        prefer_no_website: bool,
        industry_hint: str | None,
        maps_social_leads: list[dict],
    ) -> list[dict]:
        seen = set(crawled_hosts)
        for lead in maps_social_leads:
            key = lead.get("facebook_url") or lead.get("instagram_url") or lead.get("company_name")
            if key:
                seen.add(str(key).lower())

        for item in _prioritize_discovery(discovered):
            if len(leads) >= max(limit * 2, limit + 5):
                break
            url = item.get("url") or ""
            host = _host_key(url)
            if not host or host in seen:
                continue
            if should_skip_search_url(url, allow_maps_social=prefer_no_website):
                if prefer_no_website:
                    mapped = map_no_website_discovery_result(item, location, industry_hint)
                    if mapped:
                        leads.append(mapped)
                        seen.add(host)
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

    def _fast_http_enrich(
        self,
        seed_items: list[dict],
        *,
        location: str,
        industry_hint: str | None,
        limit: int,
        budget_seconds: float,
        job_control,
        metrics: ScrapeMetrics | None,
    ) -> list[dict]:
        """Sequential HTTP-only scrape with a hard wall clock — never hangs the job."""
        deadline = time.monotonic() + max(3.0, budget_seconds)
        logger.info(
            "Internet fast enrich: %s seeds · budget=%.0fs (sequential HTTP)",
            len(seed_items),
            budget_seconds,
        )
        fetcher = PageFetcher(
            timeout=4.0,
            use_playwright=False,
            metrics=metrics,
            job_control=lambda: bool(job_control and job_control()) or time.monotonic() >= deadline,
        )
        scraped: list[dict] = []
        remaining = len(seed_items)
        if metrics is not None:
            metrics.set("active_workers", 1)
            metrics.set("queue_size", remaining)
        for item in seed_items:
            if time.monotonic() >= deadline:
                break
            if job_control and job_control():
                break
            if len(scraped) >= limit:
                break
            url = (item.get("url") or "").strip()
            if not url or should_skip_search_url(url, allow_maps_social=False):
                remaining = max(0, remaining - 1)
                if metrics is not None:
                    metrics.set("queue_size", remaining)
                continue
            try:
                # Per-URL hard cap — getaddrinfo on Windows can ignore socket timeouts.
                # Do not use `with ThreadPoolExecutor` (exit waits for hung workers).
                per_url = min(5.0, max(2.0, deadline - time.monotonic()))
                one = ThreadPoolExecutor(max_workers=1)
                try:
                    fut = one.submit(
                        scrape_business_site,
                        fetcher,
                        url,
                        item.get("title"),
                        location,
                        item.get("description"),
                        industry_hint,
                        metrics,
                    )
                    try:
                        lead = fut.result(timeout=per_url)
                    except FuturesTimeoutError:
                        logger.debug("Fast enrich URL timed out: %s", url)
                        lead = None
                finally:
                    one.shutdown(wait=False, cancel_futures=True)
            except Exception as exc:
                logger.debug("Fast enrich failed for %s: %s", url, exc)
                lead = None
            remaining = max(0, remaining - 1)
            if metrics is not None:
                metrics.set("queue_size", remaining)
                metrics.inc("pages_crawled")
            if lead:
                scraped.append(lead)
        if metrics is not None:
            metrics.set("active_workers", 0)
            metrics.set("queue_size", 0)
        return self._merge_scraped_leads(scraped, location, industry_hint)

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
