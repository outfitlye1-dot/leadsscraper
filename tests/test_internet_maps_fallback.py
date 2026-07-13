from unittest.mock import MagicMock, patch

from app.models.lead import LeadStatus
from app.services.all_in_one_scraper_service import AllInOneScraperService
from app.schemas.common import ScraperStartRequest
from app.utils.scrape_sources import ScrapeSourceMode, derive_maps_search_params


MAPS_FALLBACK_LEADS = [
    {
        "company_name": "Maps Fallback Co",
        "phone": "+447911123456",
        "email": "info@mapsfb.com",
        "website": "https://mapsfb.com",
        "country": "United Kingdom",
        "source": "apify",
        "status": LeadStatus.new,
    }
]


@patch("app.services.all_in_one_scraper_service.get_settings")
@patch("app.services.all_in_one_scraper_service.EnrichmentService")
@patch("app.services.all_in_one_scraper_service.ApifyService")
def test_internet_does_not_fallback_to_maps_when_empty(mock_apify_class, mock_enrich_class, mock_settings, db_session):
    mock_settings.return_value.APIFY_ACTOR_ID = "actor-id"

    mock_apify = MagicMock()
    mock_apify._normalize_location.side_effect = lambda x: x
    mock_apify._scrape_google_maps.return_value = MAPS_FALLBACK_LEADS
    mock_apify.web_search_service.search_leads.return_value = []
    mock_apify.count_by_source.return_value = (0, 0, 0)
    mock_apify_class.return_value = mock_apify

    mock_enrich = MagicMock()
    mock_enrich.enrich_leads_batch.side_effect = lambda leads, on_progress=None: leads
    mock_enrich_class.return_value = mock_enrich

    from app.models.user import User, UserRole
    from app.models.user_api_key import ApiKeyStatus, ApiProvider, UserApiKey

    user = User(
        id=1,
        name="Test",
        email="t@test.com",
        password_hash="x",
        role=UserRole.user,
    )
    db_session.add(user)
    db_session.add(
        UserApiKey(
            user_id=1,
            provider=ApiProvider.apify,
            label="Test Apify",
            api_key="apify_api_test_key_12345",
            priority=0,
            status=ApiKeyStatus.active,
        )
    )
    db_session.commit()

    service = AllInOneScraperService(db_session)
    result = service.run(
        user,
        ScraperStartRequest(
            keyword="",
            location="London, United Kingdom",
            search_query="web design agency London UK contact email",
            limit=10,
            enrich_contacts=False,
            only_verified_contacts=False,
            auto_generate_whatsapp=False,
            scrape_source=ScrapeSourceMode.google_search,
        ),
    )

    assert result.success is True
    assert result.count == 0
    assert result.google_maps_count == 0
    assert result.google_search_count == 0
    mock_apify._scrape_google_maps.assert_not_called()


def test_derive_maps_search_params_from_query():
    kw, loc = derive_maps_search_params(
        "",
        "Berlin, Germany",
        "plumbing services Berlin Germany contact email",
    )
    assert "plumbing" in kw.lower() or "Plumbing" in kw
    assert "Germany" in loc or "Berlin" in loc
