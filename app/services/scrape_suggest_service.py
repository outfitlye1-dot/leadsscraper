from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.brain_repository import BrainRepository
from app.schemas.message import ScrapeSuggestRequest, ScrapeSuggestResponse
from app.services.groq_service import GroqService
from app.utils.scrape_suggest import location_from_brain_notes, suggest_scrape_from_profile_rules

_GENERIC_PROFILE: dict = {
    "name": None,
    "services": [],
    "skills": [],
    "experience": [],
    "education": [],
    "projects": [],
    "tools": [],
    "technologies": [],
    "professional_summary": None,
    "custom_notes": "",
}


def _strip_ai_locations(result: dict) -> dict:
    """Location is always user-provided in the scraper form, never from AI."""
    result["recommended_location"] = ""
    result["location_suggestions"] = []
    return result


class ScrapeSuggestService:
    def __init__(self, db: Session):
        self.brain_repository = BrainRepository(db)
        self.groq_service = GroqService(db)

    def _profile_from_brain(self, brain) -> dict:
        return {
            "name": brain.name,
            "skills": brain.skills or [],
            "experience": brain.experience or [],
            "education": brain.education or [],
            "projects": brain.projects or [],
            "services": brain.services or [],
            "tools": brain.tools or [],
            "technologies": brain.technologies or [],
            "professional_summary": brain.professional_summary,
            "custom_notes": brain.custom_notes,
            "source": "brain",
        }

    def get_brain_profile(self, user_id: int) -> dict | None:
        brain = self.brain_repository.get_by_user(user_id)
        if brain and (
            brain.name
            or brain.services
            or brain.skills
            or brain.professional_summary
            or brain.custom_notes
        ):
            return self._profile_from_brain(brain)
        return None

    def user_location_from_brain_notes(self, user_id: int) -> str | None:
        profile = self.get_brain_profile(user_id)
        if not profile:
            return None
        return location_from_brain_notes(profile)

    def _normalize_scrape_source(self, scrape_source: str) -> str:
        if scrape_source in {"all", "google_maps", "google_search", "meta_ads"}:
            return scrape_source
        return "all"

    def _rule_based_suggest(self, profile: dict, scrape_source: str) -> dict:
        result = suggest_scrape_from_profile_rules(profile, scrape_source)
        result = _strip_ai_locations(result)
        result["has_profile"] = bool(
            profile.get("name")
            or profile.get("services")
            or profile.get("skills")
            or profile.get("professional_summary")
            or profile.get("custom_notes")
        )
        return result

    def _finalize_suggest(self, result: dict, profile: dict | None) -> ScrapeSuggestResponse:
        result["user_location"] = (location_from_brain_notes(profile) or "") if profile else ""
        if not result.get("recommended_keyword"):
            result["recommended_keyword"] = (
                result["keyword_suggestions"][0] if result.get("keyword_suggestions") else "business"
            )
        if not result.get("recommended_search_query"):
            result["recommended_search_query"] = (
                result["search_queries"][0] if result.get("search_queries") else ""
            )
        return ScrapeSuggestResponse(**result)

    def suggest(self, user: User, data: ScrapeSuggestRequest) -> ScrapeSuggestResponse:
        self.groq_service.user_id = user.id
        scrape_source = self._normalize_scrape_source(data.scrape_source)
        profile = self.get_brain_profile(user.id)

        if not profile:
            result = self._rule_based_suggest(_GENERIC_PROFILE, scrape_source)
            result["has_profile"] = False
            return self._finalize_suggest(result, None)

        if not self.groq_service._has_groq_access():
            result = self._rule_based_suggest(profile, scrape_source)
            return self._finalize_suggest(result, profile)

        result = self.groq_service.suggest_scrape_from_profile(profile, scrape_source)
        result = _strip_ai_locations(result)
        return self._finalize_suggest(result, profile)
