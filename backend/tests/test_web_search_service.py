from unittest.mock import MagicMock, patch

from app.services.web_search_service import WebSearchService


@patch("app.services.web_search_service.run_business_spider")
@patch("app.services.web_search_service.SearchDiscovery")
def test_web_search_service_with_query(mock_discovery_class, mock_run_spider):
    mock_discovery = MagicMock()
    mock_discovery.search.return_value = [
        {
            "title": "Acme Agency",
            "url": "https://acmeagency.com",
            "description": "Email info@acmeagency.com for web design in Karachi",
        }
    ]
    mock_discovery_class.return_value = mock_discovery

    mock_run_spider.return_value = []

    leads = WebSearchService().search_leads(
        "",
        "",
        5,
        search_query="web design agency Karachi Pakistan",
    )
    assert len(leads) == 1
    assert leads[0]["company_name"] == "Acme Agency"
    mock_discovery.search.assert_called_once()
    assert mock_discovery.search.call_args.kwargs.get("search_query")


@patch("app.services.web_search_service.run_business_spider")
@patch("app.services.web_search_service.SearchDiscovery")
def test_web_search_service(mock_discovery_class, mock_run_spider):
    mock_discovery = MagicMock()
    mock_discovery.search.return_value = [
        {
            "title": "Acme Agency",
            "url": "https://acmeagency.com",
            "description": "Email info@acmeagency.com for web design in Karachi",
        }
    ]
    mock_discovery_class.return_value = mock_discovery

    mock_run_spider.return_value = [
        {
            "company_name": "Acme Agency",
            "website": "https://acmeagency.com",
            "email": "info@acme.com",
            "phone": None,
            "linkedin_url": None,
            "instagram_url": None,
            "notes": "Web design in Karachi",
            "source": "web_search",
        }
    ]

    leads = WebSearchService().search_leads("web agency", "Karachi, Pakistan", 5)
    assert len(leads) == 1
    assert leads[0]["company_name"] == "Acme Agency"
    assert leads[0]["source"] == "web_search"
    mock_run_spider.assert_called_once()


@patch("app.services.web_search_service.run_business_spider")
@patch("app.services.web_search_service.SearchDiscovery")
def test_web_search_service_fallback(mock_discovery_class, mock_run_spider):
    mock_discovery = MagicMock()
    mock_discovery.search.return_value = [
        {
            "title": "Beta Studio",
            "url": "https://betastudio.com",
            "description": "Design studio. WhatsApp 0300-1234567",
        }
    ]
    mock_discovery_class.return_value = mock_discovery
    mock_run_spider.return_value = []

    leads = WebSearchService().search_leads("design", "Lahore, Pakistan", 5)
    assert len(leads) == 1
    assert leads[0]["company_name"] == "Beta Studio"
