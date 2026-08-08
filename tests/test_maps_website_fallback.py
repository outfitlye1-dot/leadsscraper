from unittest.mock import MagicMock, patch

from app.models.lead import LeadStatus
from app.schemas.common import ScraperStartRequest
from app.services.all_in_one_scraper_service import AllInOneScraperService
from app.utils.scrape_sources import ScrapeSourceMode
from app.utils.website_utils import WebsiteFilter


WEB_LEADS_WITH_SITES = [
    {
        "company_name": "Big Restaurant",
        "phone": "+447911123456",
        "email": "info@big.com",
        "website": "https://bigrestaurant.com",
        "country": "United Kingdom",
        "source": "web_search",
        "status": LeadStatus.new,
    }
]

MAPS_NO_WEBSITE = [
    {
        "company_name": "Local Cafe",
        "phone": "+447922123456",
        "email": None,
        "website": None,
        "country": "United Kingdom",
        "source": "playwright_maps",
        "status": LeadStatus.new,
    }
]


def _seed_users(db_session):
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
    return user


@patch("app.services.all_in_one_scraper_service.get_settings")
@patch("app.services.all_in_one_scraper_service.EnrichmentService")
@patch("app.services.all_in_one_scraper_service.ApifyService")
def test_internet_uses_playwright_maps_not_silent_all_fallback(
    mock_apify_class, mock_enrich_class, mock_settings, db_session
):
    """Internet primary is Playwright Maps; website filter must not re-trigger All-mode Maps fallback."""
    mock_settings.return_value.SCRAPER_INTERNET_MAX_SECONDS = 40.0

    mock_apify = MagicMock()
    mock_apify._normalize_location.side_effect = lambda x: x
    mock_apify.scrape_maps_playwright_local.return_value = MAPS_NO_WEBSITE
    mock_apify.web_search_service.search_leads.return_value = WEB_LEADS_WITH_SITES
    mock_apify.count_by_source.return_value = (1, 0, 0)
    mock_apify_class.return_value = mock_apify

    mock_enrich = MagicMock()
    mock_enrich.enrich_leads_batch.side_effect = lambda leads, on_progress=None: leads
    mock_enrich_class.return_value = mock_enrich

    user = _seed_users(db_session)
    service = AllInOneScraperService(db_session)
    result = service.run(
        user,
        ScraperStartRequest(
            keyword="restaurant",
            location="London, United Kingdom",
            search_query="restaurant London",
            limit=10,
            enrich_contacts=False,
            only_verified_contacts=False,
            auto_generate_whatsapp=False,
            website_filter=WebsiteFilter.without_website,
            scrape_source=ScrapeSourceMode.google_search,
            include_meta_ads=False,
        ),
    )

    assert result.success is True
    mock_apify.scrape_maps_playwright_local.assert_called()
    # Primary Maps call only — website filter must not invoke a second All-source Maps pass
    assert mock_apify.scrape_maps_playwright_local.call_count == 1


@patch("app.services.all_in_one_scraper_service.get_settings")
@patch("app.services.all_in_one_scraper_service.EnrichmentService")
@patch("app.services.all_in_one_scraper_service.ApifyService")
def test_all_source_may_fallback_to_maps_when_website_filter_removes_leads(
    mock_apify_class, mock_enrich_class, mock_settings, db_session
):
    mock_settings.return_value.SCRAPER_PLAYWRIGHT_MAPS_MAX_SECONDS = 90.0

    mock_apify = MagicMock()
    mock_apify._normalize_location.side_effect = lambda x: x
    # First parallel Maps call returns empty; website filter fallback rescrapes Maps
    mock_apify.scrape_maps_playwright_local.side_effect = [[], MAPS_NO_WEBSITE]
    mock_apify.web_search_service.search_leads.return_value = WEB_LEADS_WITH_SITES
    mock_apify.count_by_source.side_effect = [(0, 1, 0), (1, 0, 0)]
    mock_apify_class.return_value = mock_apify

    mock_enrich = MagicMock()
    mock_enrich.enrich_leads_batch.side_effect = lambda leads, on_progress=None: leads
    mock_enrich_class.return_value = mock_enrich

    user = _seed_users(db_session)
    service = AllInOneScraperService(db_session)
    result = service.run(
        user,
        ScraperStartRequest(
            keyword="restaurant",
            location="London, United Kingdom",
            search_query="restaurant London",
            limit=10,
            enrich_contacts=False,
            only_verified_contacts=False,
            auto_generate_whatsapp=False,
            website_filter=WebsiteFilter.without_website,
            scrape_source=ScrapeSourceMode.all,
            include_meta_ads=False,
        ),
    )

    assert result.success is True
    assert result.count == 1
    assert mock_apify.scrape_maps_playwright_local.call_count >= 2
