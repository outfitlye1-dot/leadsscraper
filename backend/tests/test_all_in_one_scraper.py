from unittest.mock import MagicMock, patch

from app.models.lead import LeadStatus
from app.services.all_in_one_scraper_service import AllInOneScraperService
from app.schemas.common import ScraperStartRequest
from app.utils.scrape_sources import ScrapeSourceMode


MOCK_LEADS = [
    {
        "company_name": "Acme Corp",
        "phone": "03001234567",
        "email": "info@acme.com",
        "website": None,
        "country": "Pakistan",
        "source": "playwright_maps",
        "status": LeadStatus.new,
    }
]


@patch("app.services.all_in_one_scraper_service.get_settings")
@patch("app.services.all_in_one_scraper_service.EnrichmentService")
@patch("app.services.all_in_one_scraper_service.ApifyService")
def test_all_in_one_scraper(mock_apify_class, mock_enrich_class, mock_settings, db_session):
    mock_settings.return_value.SCRAPER_PLAYWRIGHT_MAPS_MAX_SECONDS = 90.0

    mock_apify = MagicMock()
    mock_apify._normalize_location.side_effect = lambda x: x
    mock_apify.scrape_maps_playwright_local.return_value = MOCK_LEADS
    mock_apify.web_search_service.search_leads.return_value = []
    mock_apify.count_by_source.return_value = (1, 0, 0)
    mock_apify_class.return_value = mock_apify

    mock_enrich = MagicMock()
    mock_enrich.enrich_lead.side_effect = lambda x: x
    mock_enrich.enrich_leads_batch.side_effect = lambda leads, on_progress=None, **kwargs: leads
    mock_enrich_class.return_value = mock_enrich

    from app.models.user import User, UserRole

    user = User(
        id=1,
        name="Test",
        email="t@test.com",
        password_hash="x",
        role=UserRole.user,
    )
    db_session.add(user)
    db_session.commit()

    progress_calls: list[tuple[int, str, str]] = []

    def on_progress(percent, stage, message):
        progress_calls.append((percent, stage, message))

    service = AllInOneScraperService(db_session)
    result = service.run(
        user,
        ScraperStartRequest(
            keyword="agency",
            location="Karachi, Pakistan",
            limit=10,
            enrich_contacts=True,
            auto_generate_whatsapp=False,
            scrape_source=ScrapeSourceMode.google_maps,
        ),
        on_progress=on_progress,
    )

    assert result.success is True
    assert result.count == 1
    assert result.emails_found == 1
    assert result.whatsapp_numbers_found == 1
    assert len(progress_calls) > 0
    assert progress_calls[-1][0] == 100
    mock_apify.scrape_maps_playwright_local.assert_called()
