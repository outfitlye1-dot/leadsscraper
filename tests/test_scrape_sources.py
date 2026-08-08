from app.utils.scrape_sources import (
    clean_search_title,
    dedupe_leads,
    map_web_search_result,
    should_skip_search_url,
)
from app.utils.contact_utils import extract_phones_from_text, is_whatsapp_ready, normalize_whatsapp_phone


def test_should_skip_google():
    assert should_skip_search_url("https://www.google.com/search?q=test")
    assert not should_skip_search_url("https://acme.com")


def test_extract_phones_whatsapp_send_url():
    text = 'href="https://api.whatsapp.com/send?phone=923331234567&text=Hi"'
    phones = extract_phones_from_text(text, "Pakistan")
    assert phones and "923331234567" in phones[0].replace("+", "")


def test_extract_phones_from_snippet_text():
    text = "Best restaurant in Karachi. WhatsApp: 0300-1234567 for bookings"
    phones = extract_phones_from_text(text, "Pakistan")
    assert phones
    assert normalize_whatsapp_phone(phones[0], "Pakistan") == "923001234567"


def test_extract_business_name_from_title_home_pipe():
    from app.utils.scrape_sources import extract_business_name_from_title

    name = extract_business_name_from_title(
        "Home | Acme Web Design Karachi",
        "https://acmeweb.com",
    )
    assert name == "Acme Web Design Karachi"


def test_extract_business_name_prefers_brand_over_home():
    from app.utils.scrape_sources import extract_business_name_from_title

    name = extract_business_name_from_title(
        "Welcome - Pizza Planet Restaurant",
        "https://pizzaplanet.com",
    )
    assert "Pizza Planet" in name


def test_derive_industry_hint():
    from app.utils.scrape_sources import derive_industry_hint

    assert derive_industry_hint("", "web design agency Karachi Pakistan") == "Web Design Agency Karachi Pakistan"
    assert derive_industry_hint("restaurant", "London") == "Restaurant"


def test_map_web_search_result():
    lead = map_web_search_result(
        {
            "title": "Home | Acme Web Design",
            "url": "https://acmeweb.com",
            "description": "Contact info@acmeweb.com for web design in Karachi",
        },
        "Karachi, Pakistan",
        "Web Design Agency",
    )
    assert lead is not None
    assert lead["company_name"] == "Acme Web Design"
    assert lead["website"] == "https://acmeweb.com"
    assert lead["source"] == "web_search"
    assert lead.get("email") == "info@acmeweb.com"
    assert lead.get("category") == "Web Design Agency"


def test_map_web_search_result_discovery_only_accepts_real_website():
    """Discovery-only keeps real business websites even without phone/email yet."""
    lead = map_web_search_result(
        {
            "title": "Acme Web Design",
            "url": "https://acmeweb.com",
            "description": "We build websites in Karachi",
        },
        "Karachi, Pakistan",
        discovery_only=True,
    )
    assert lead is not None
    assert lead.get("website")
    assert lead.get("company_name") == "Acme Web Design"

    with_contact = map_web_search_result(
        {
            "title": "Acme Web Design",
            "url": "https://acmeweb.com",
            "description": "Email info@acmeweb.com or call 03001234567",
        },
        "Karachi, Pakistan",
        discovery_only=True,
    )
    assert with_contact is not None
    assert with_contact.get("email") or with_contact.get("phone")


def test_map_web_search_result_rejects_listicle():
    lead = map_web_search_result(
        {
            "title": "Top 10 Web Design Agencies in Karachi",
            "url": "https://blog.example.com/top-10",
            "description": "A list of agencies",
        },
        "Karachi, Pakistan",
    )
    assert lead is None


def test_map_web_search_result_extracts_whatsapp_from_description():
    lead = map_web_search_result(
        {
            "title": "Acme Restaurant",
            "url": "https://acmerestaurant.com",
            "description": "Call us on WhatsApp 0333-1234567 in Karachi",
        },
        "Karachi",
    )
    assert lead is not None
    assert lead.get("phone")
    assert is_whatsapp_ready(lead["phone"], lead.get("country"))


def test_map_web_search_accepts_gmail_from_snippet():
    lead = map_web_search_result(
        {
            "title": "Acme Web Design",
            "url": "https://acmeweb.co.uk",
            "description": "Email hello@gmail.com for a free quote in London",
        },
        "London, United Kingdom",
    )
    assert lead is not None
    assert lead.get("email") == "hello@gmail.com"


def test_dedupe_leads_merges_same_domain():
    a = {"company_name": "A", "website": "https://acme.com", "phone": "+921", "source": "apify"}
    b = {
        "company_name": "Acme",
        "website": "https://www.acme.com",
        "email": "a@acme.com",
        "source": "web_search",
    }
    merged = dedupe_leads([a, b])
    assert len(merged) == 1
    assert merged[0].get("phone")
    assert merged[0].get("email")


def test_should_skip_designrush_directory():
    assert should_skip_search_url(
        "https://www.designrush.com/agency/web-development-companies/uk/london"
    )


def test_should_skip_listicle_url_path():
    assert should_skip_search_url(
        "https://www.bluelinks.agency/web-design/listicles/web-development-companies-in-london-uk/"
    )


def test_rejects_top_companies_listicle_title():
    from app.utils.scrape_sources import is_listicle_or_bad_title

    assert is_listicle_or_bad_title("Top Web Development Companies in London")


def test_rejects_seo_presents_title():
    from app.utils.scrape_sources import is_listicle_or_bad_title

    assert is_listicle_or_bad_title("Mobit Solutions Presents Cost Effective IT Solutions")


def test_map_web_search_rejects_designrush():
    lead = map_web_search_result(
        {
            "title": "Top Web Development Companies in London",
            "url": "https://www.designrush.com/agency/web-development-companies/uk/london",
            "description": "marketplace@designrush.com",
        },
        "London, United Kingdom",
    )
    assert lead is None


def test_title_conflicts_with_europe_search():
    from app.utils.scrape_sources import title_conflicts_with_location

    assert title_conflicts_with_location(
        "Web Development Agency Lahore Pakistan",
        "London, United Kingdom",
    )
    assert not title_conflicts_with_location(
        "London Web Design Agency",
        "London, United Kingdom",
    )


def test_quality_gate_rejects_wrong_region_phone():
    from app.utils.lead_contacts import sanitize_lead_contacts
    from app.utils.scrape_sources import is_quality_business_lead

    lead = {
        "company_name": "Revatics",
        "website": "https://www.revatics.co.uk/",
        "email": "contact@revatics.co.uk",
        "phone": "+919106686124",
        "country": "UK",
        "source": "web_search",
    }
    cleaned = sanitize_lead_contacts(lead, search_location="London, United Kingdom")
    assert cleaned.get("phone") is None
    assert is_quality_business_lead(cleaned, search_location="London, United Kingdom")
