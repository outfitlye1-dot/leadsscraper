"""Public demo scrape — 4 leads from web search, no auth, no DB save."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from app.scraper.metrics import ScrapeMetrics
from app.schemas.common import DemoLeadItem, DemoScrapeResponse
from app.services.web_search_service import WebSearchService
from app.utils.contact_utils import is_valid_email, is_whatsapp_ready
from app.utils.scrape_defaults import normalize_location_alias, resolve_scrape_location

logger = logging.getLogger(__name__)

DEMO_LEAD_LIMIT = 4
# Keep under typical Next.js rewrite / browser proxy timeouts (~30–60s)
DEMO_MAX_SECONDS = 15.0


class DemoScrapeService:
    def run(self, keyword: str, location: str) -> DemoScrapeResponse:
        keyword = (keyword or "web design agency").strip()
        location = normalize_location_alias(
            resolve_scrape_location((location or "Berlin, Germany").strip())
        )
        search_query = f"{keyword} {location} contact email phone"

        metrics = ScrapeMetrics()
        web = WebSearchService()

        def _search() -> list[dict]:
            return web.search_leads(
                keyword,
                location,
                DEMO_LEAD_LIMIT,
                search_query=search_query,
                metrics=metrics,
                max_seconds=DEMO_MAX_SECONDS,
                light=True,
            )

        pool = ThreadPoolExecutor(max_workers=1)
        try:
            fut = pool.submit(_search)
            # Do NOT use `with ThreadPoolExecutor` — on timeout its shutdown(wait=True)
            # blocks until the hung search finishes and defeats the whole budget.
            leads = fut.result(timeout=DEMO_MAX_SECONDS + 3.0)
        except FuturesTimeoutError:
            logger.warning("Demo scrape timed out after %.0fs", DEMO_MAX_SECONDS)
            return DemoScrapeResponse(
                success=True,
                count=0,
                total_estimated=0,
                message="Demo timed out — try again, or create an account for full scrapes.",
                leads=[],
            )
        except Exception as exc:
            logger.warning("Demo scrape failed: %s", exc)
            return DemoScrapeResponse(
                success=False,
                count=0,
                total_estimated=0,
                message="Demo scrape failed. Please try again in a moment.",
                leads=[],
            )
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        if not leads:
            return DemoScrapeResponse(
                success=True,
                count=0,
                total_estimated=0,
                message="No leads found for this search. Try a different keyword or city.",
                leads=[],
            )

        # Skip heavy enrichment on the public demo — stay fast for the landing proxy.
        items: list[DemoLeadItem] = []
        for lead in leads[:DEMO_LEAD_LIMIT]:
            email = lead.get("email")
            phone = lead.get("phone")
            country = lead.get("country")
            verified = bool(
                (email and is_valid_email(email))
                or (phone and is_whatsapp_ready(phone, country))
            )
            items.append(
                DemoLeadItem(
                    company_name=(lead.get("company_name") or "Unknown").strip(),
                    email=email,
                    phone=phone,
                    website=lead.get("website"),
                    city=lead.get("city"),
                    country=country,
                    verified=verified,
                )
            )

        if not items:
            return DemoScrapeResponse(
                success=True,
                count=0,
                total_estimated=0,
                message="No business leads matched. Try another keyword or location.",
                leads=[],
            )

        total_estimated = max(
            int(metrics.pages_discovered or 0) * 4,
            int(metrics.leads_parsed or 0),
            len(items) * 12,
            len(items),
        )

        return DemoScrapeResponse(
            success=True,
            count=len(items),
            total_estimated=total_estimated,
            message=f"Preview: {len(items)} of ~{total_estimated} matches — create account for full export.",
            leads=items,
        )
