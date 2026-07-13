from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.daily_scrape_repository import DailyScrapeRepository
from app.schemas.common import (
    DailyScrapeStartResponse,
    DailyScrapeStatusResponse,
    ScraperStartRequest,
)
from app.schemas.message import ScrapeSuggestRequest
from app.services.scrape_suggest_service import ScrapeSuggestService
from app.services.scraper_runner import start_scraper_job
from app.utils.scrape_sources import ScrapeSourceMode
from app.utils.website_utils import WebsiteFilter

DAILY_LEADS_TARGET = 100


class DailyScrapeService:
    def __init__(self, db: Session):
        self.db = db
        self.daily_repo = DailyScrapeRepository(db)
        self.suggest_service = ScrapeSuggestService(db)

    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()

    def get_status(self, user: User) -> DailyScrapeStatusResponse:
        today = self._today()
        today_run = self.daily_repo.get_for_user_date(user.id, today)
        latest = self.daily_repo.get_latest_for_user(user.id)

        preview_query = ""
        profile_name = None
        try:
            suggestions = self.suggest_service.suggest(
                user, ScrapeSuggestRequest(scrape_source="google_maps")
            )
            preview_query = (
                suggestions.recommended_search_query
                or suggestions.recommended_keyword
                or ""
            )
            profile_name = suggestions.profile_name
        except HTTPException:
            pass
        except Exception:
            pass

        return DailyScrapeStatusResponse(
            can_run=today_run is None,
            leads_target=DAILY_LEADS_TARGET,
            run_date=today.isoformat(),
            last_run_date=latest.run_date.isoformat() if latest else None,
            last_job_id=latest.job_id if latest else None,
            preview_search_query=preview_query,
            profile_name=profile_name,
            has_profile=bool(preview_query or profile_name),
        )

    def start(self, user: User) -> DailyScrapeStartResponse:
        today = self._today()
        if self.daily_repo.get_for_user_date(user.id, today):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Aaj ka daily scrape already run ho chuka hai. Kal dubara try karein.",
            )

        suggestions = self.suggest_service.suggest(
            user, ScrapeSuggestRequest(scrape_source="google_maps")
        )
        keyword = (suggestions.recommended_keyword or "").strip()
        location = (self.suggest_service.user_location_from_brain_notes(user.id) or "").strip()
        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Brain se keyword generate nahi ho saki. Pehle Brain profile complete karein.",
            )
        if not location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Location chahiye. Scraper form mein khud location daalein, "
                    "ya Brain custom notes mein city likhein (e.g. Lahore, Pakistan)."
                ),
            )

        payload = ScraperStartRequest(
            keyword=keyword,
            location=location,
            limit=DAILY_LEADS_TARGET,
            scrape_source=ScrapeSourceMode.google_maps,
            website_filter=WebsiteFilter.without_website,
            enrich_contacts=True,
            only_verified_contacts=False,
            auto_generate_whatsapp=False,
        )
        job_id = start_scraper_job(user.id, payload)
        self.daily_repo.create(
            user.id,
            today,
            job_id,
            leads_target=DAILY_LEADS_TARGET,
            search_query=f"{keyword} — {location} (no website)",
        )

        return DailyScrapeStartResponse(
            job_id=job_id,
            leads_target=DAILY_LEADS_TARGET,
            search_query=f"{keyword} in {location}",
            message=(
                f"Daily {DAILY_LEADS_TARGET} local leads scrape shuru — "
                f"Brain AI keyword + aapki location: businesses without website."
            ),
        )
