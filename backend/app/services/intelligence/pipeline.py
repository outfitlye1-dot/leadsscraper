"""Orchestrates the lead intelligence pipeline after scraping."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.scraper.validators.quality import apply_quality_to_lead
from app.services.intelligence.advanced_dedup import mark_batch_duplicates
from app.services.intelligence.buying_intent_service import calculate_buying_intent
from app.services.intelligence.contact_verification_service import verify_lead_contacts
from app.services.intelligence.lead_qualification_service import qualify_lead_rules
from app.services.intelligence.niche_intelligence import apply_niche_intelligence
from app.services.intelligence.social_intelligence_service import analyze_social_presence
from app.services.intelligence.website_audit_service import audit_website_from_html, audit_website_lightweight
from app.scrapers.fetcher import PageFetcher
from app.utils.lead_db_fields import strip_lead_dict

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceStats:
    total_scraped: int = 0
    duplicates_removed: int = 0
    invalid_contacts: int = 0
    no_phone_leads: int = 0
    qualified_leads: int = 0
    hot_leads: int = 0
    warm_leads: int = 0
    cold_leads: int = 0
    avg_opportunity_score: float = 0.0
    avg_buying_intent: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_scraped": self.total_scraped,
            "duplicates_removed": self.duplicates_removed,
            "invalid_contacts": self.invalid_contacts,
            "no_phone_leads": self.no_phone_leads,
            "qualified_leads": self.qualified_leads,
            "hot_leads": self.hot_leads,
            "warm_leads": self.warm_leads,
            "cold_leads": self.cold_leads,
            "avg_opportunity_score": round(self.avg_opportunity_score, 1),
            "avg_buying_intent": round(self.avg_buying_intent, 1),
        }


class LeadIntelligencePipeline:
    """
    Scrape Sources → Clean → Dedup → Verify → Website Audit → Social → Qualify → Score → Save
    """

    def __init__(self, db: Session | None = None, user_id: int | None = None):
        self.db = db
        self.user_id = user_id

    def process_batch(
        self,
        leads: list[dict],
        *,
        existing_leads: list | None = None,
        search_location: str | None = None,
        audit_websites: bool = True,
    ) -> tuple[list[dict], IntelligenceStats]:
        stats = IntelligenceStats(total_scraped=len(leads))
        if not leads:
            return [], stats

        if existing_leads is not None:
            leads, dup_removed = mark_batch_duplicates(leads, existing_leads)
            stats.duplicates_removed = dup_removed

        fetcher = PageFetcher(use_playwright=False) if audit_websites else None
        processed: list[dict] = []
        opp_scores: list[int] = []
        intent_scores: list[int] = []

        for lead in leads:
            try:
                lead = self._process_one(lead, search_location, fetcher, audit_websites)
                lead.pop("_duplicate_risk", None)
                lead = apply_quality_to_lead(strip_lead_dict(lead))
                processed.append(lead)

                if not lead.get("phone_verified") and not lead.get("phone"):
                    stats.no_phone_leads += 1
                if not lead.get("phone_verified") and not lead.get("email_verified"):
                    stats.invalid_contacts += 1
                if lead.get("ai_qualification") == "qualified":
                    stats.qualified_leads += 1
                tier = lead.get("intent_tier")
                if tier == "hot":
                    stats.hot_leads += 1
                elif tier == "warm":
                    stats.warm_leads += 1
                elif tier == "cold":
                    stats.cold_leads += 1
                if lead.get("website_opportunity_score") is not None:
                    opp_scores.append(lead["website_opportunity_score"])
                if lead.get("buying_intent_score") is not None:
                    intent_scores.append(lead["buying_intent_score"])
            except Exception as exc:
                logger.debug("Intelligence pipeline skip lead: %s", exc)

        if opp_scores:
            stats.avg_opportunity_score = sum(opp_scores) / len(opp_scores)
        if intent_scores:
            stats.avg_buying_intent = sum(intent_scores) / len(intent_scores)

        return processed, stats

    def _process_one(
        self,
        lead: dict,
        search_location: str | None,
        fetcher: PageFetcher | None,
        audit_websites: bool,
    ) -> dict:
        loc = search_location or lead.get("country")
        lead = verify_lead_contacts(lead, loc)

        if audit_websites and lead.get("website"):
            html, final_url, load_ms = None, lead.get("website"), None
            if fetcher:
                start = time.perf_counter()
                html, final_url = fetcher.fetch(lead["website"])
                load_ms = int((time.perf_counter() - start) * 1000)
                if final_url:
                    lead["website"] = final_url
            lead = audit_website_from_html(
                lead, html, fetch_ok=bool(html), load_time_ms=load_ms
            )
        else:
            lead = audit_website_lightweight(lead)

        lead = analyze_social_presence(lead)
        lead = apply_niche_intelligence(lead)
        lead = calculate_buying_intent(lead)
        lead = qualify_lead_rules(lead)
        return lead
