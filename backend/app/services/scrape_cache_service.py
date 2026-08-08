"""Serve manual scrapes from background leads already stored in the database."""

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.repositories.lead_repository import LeadRepository
from app.schemas.common import ScraperStartRequest, ScraperStartResponse
from app.utils.website_utils import has_real_website


class ScrapeCacheService:
    def __init__(self, db: Session):
        self.lead_repository = LeadRepository(db)

    def find_matching_leads(self, user_id: int, data: ScraperStartRequest) -> list[Lead]:
        return self.lead_repository.find_background_for_scrape_request(
            user_id, data, data.limit
        )

    def try_fulfill_from_cache(
        self, user_id: int, data: ScraperStartRequest
    ) -> ScraperStartResponse | None:
        matched = self.find_matching_leads(user_id, data)
        if not matched:
            return None

        lead_ids = [lead.id for lead in matched]
        self.lead_repository.promote_background_leads(user_id, lead_ids)
        with_site = sum(1 for lead in matched if has_real_website(lead.website))
        return ScraperStartResponse(
            success=True,
            count=len(matched),
            message=(
                f"Loaded {len(matched)} lead(s) from database cache for "
                f"'{data.keyword or data.search_query}' in '{data.location}' — no live scrape needed."
            ),
            leads_discovered=len(matched),
            with_website=with_site,
            without_website=len(matched) - with_site,
            saved_lead_ids=lead_ids,
            skipped_duplicates=0,
        )
