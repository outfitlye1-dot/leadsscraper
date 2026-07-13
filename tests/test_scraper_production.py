"""Unit tests for production scraper modules."""

from app.scraper.metrics import ScrapeMetrics
from app.scraper.utils.dedup import dedupe_leads_production
from app.scraper.validators.email_validator import validate_email
from app.scraper.validators.phone_validator import validate_phone, validate_whatsapp_phone
from app.scraper.validators.quality import QUALITY_HIGH, apply_quality_to_lead, score_lead_quality
from app.scraper.validators.website_validator import validate_website, website_host
from app.scrapers.parser import extract_contacts_from_html


def test_dedupe_by_email_phone_website():
    leads = [
        {
            "company_name": "Acme A",
            "email": "info@acme.com",
            "website": "https://www.acme.com",
            "phone": "+923001234567",
            "country": "Pakistan",
        },
        {
            "company_name": "Acme B",
            "email": "info@acme.com",
            "website": "https://acme.com/contact",
            "phone": None,
            "country": "Pakistan",
        },
        {
            "company_name": "Other Co",
            "email": "hello@other.com",
            "website": "https://other.com",
            "phone": "+923009999999",
            "country": "Pakistan",
        },
    ]
    result = dedupe_leads_production(leads)
    assert len(result) == 2
    names = {lead["company_name"] for lead in result}
    assert "Other Co" in names


def test_quality_scoring_high():
    lead = {
        "company_name": "Acme Web",
        "website": "https://acme.com",
        "email": "info@acme.com",
        "phone": "03001234567",
        "country": "Pakistan",
        "address": "123 Main St",
        "city": "Karachi",
        "linkedin_url": "https://linkedin.com/company/acme",
    }
    scored = apply_quality_to_lead(lead)
    assert scored["quality_score"] >= 70
    assert scored["quality_tier"] == QUALITY_HIGH


def test_validators():
    assert validate_email("info@acme.com") is True
    assert validate_email("not-an-email") is False
    assert validate_website("https://acme.com") is True
    assert validate_website("https://facebook.com/page") is False
    assert website_host("https://www.acme.com/path") == "acme.com"
    assert validate_phone("03001234567", "Pakistan") is True
    assert validate_whatsapp_phone("03001234567", "Pakistan") is True


def test_extract_contacts_address_and_facebook():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type":"LocalBusiness","name":"Pizza Planet","telephone":"03001234567",
     "address":{"streetAddress":"42 Galaxy Road","addressLocality":"Karachi","addressCountry":"Pakistan"},
     "founder":{"@type":"Person","name":"John Doe"}}
    </script>
    </head><body>
    <a href="https://facebook.com/pizzaplanet">FB</a>
    <a href="mailto:orders@pizzaplanet.com">Email</a>
    </body></html>
    """
    data = extract_contacts_from_html(html, "https://pizzaplanet.com", "Pakistan")
    assert data["contact_name"] == "John Doe"
    assert "Galaxy Road" in (data.get("address") or "")
    assert data.get("city") == "Karachi"
    assert data.get("facebook_url") and "facebook.com" in data["facebook_url"]
    assert data.get("email") == "orders@pizzaplanet.com"


def test_scrape_metrics_success_rate():
    metrics = ScrapeMetrics()
    metrics.inc("pages_fetched", 8)
    metrics.inc("pages_failed", 2)
    assert metrics.success_rate == 80.0
    dashboard = metrics.to_dict()
    assert dashboard["pages_fetched"] == 8


def test_score_lead_quality_tiers():
    score, tier = score_lead_quality({"company_name": "X"})
    assert tier in ("high", "medium", "low")
    assert 0 <= score <= 100
