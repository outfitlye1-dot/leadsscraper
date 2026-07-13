from unittest.mock import patch

from app.services.demo_scrape_service import DEMO_LEAD_LIMIT, DemoScrapeService
from app.utils.demo_rate_limit import allow_demo_request


def test_demo_lead_limit_constant():
    assert DEMO_LEAD_LIMIT == 4


def test_demo_rate_limit_blocks_after_max():
    ip = "test-ip-unique-1"
    for _ in range(5):
        assert allow_demo_request(ip) is True
    assert allow_demo_request(ip) is False


@patch("app.services.demo_scrape_service.WebSearchService")
@patch("app.services.demo_scrape_service.EnrichmentService")
def test_demo_scrape_returns_leads(mock_enrich_cls, mock_web_cls):
    mock_web_cls.return_value.search_leads.return_value = [
        {
            "company_name": "Acme GmbH",
            "email": "hello@acme.de",
            "phone": "+49 30 1234567",
            "website": "https://acme.de",
            "city": "Berlin",
            "country": "Germany",
        }
    ]
    mock_enrich_cls.return_value.enrich_leads_batch.side_effect = lambda leads, **_: leads

    result = DemoScrapeService().run("web agency", "Berlin, Germany")

    assert result.success is True
    assert result.count == 1
    assert result.leads[0].company_name == "Acme GmbH"
    assert result.leads[0].verified is True
    mock_web_cls.return_value.search_leads.assert_called_once()
    call_kwargs = mock_web_cls.return_value.search_leads.call_args
    assert call_kwargs[0][2] == DEMO_LEAD_LIMIT


@patch("app.services.demo_scrape_service.WebSearchService")
def test_demo_scrape_empty_results(mock_web_cls):
    mock_web_cls.return_value.search_leads.return_value = []
    result = DemoScrapeService().run("xyz", "Nowhere")
    assert result.count == 0
    assert result.leads == []
