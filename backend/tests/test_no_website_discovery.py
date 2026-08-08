from app.models.lead import LeadStatus
from app.utils.scrape_sources import map_no_website_discovery_result


def test_map_no_website_from_google_maps_snippet():
    lead = map_no_website_discovery_result(
        {
            "title": "Joe's Pizza - Google Maps",
            "url": "https://www.google.com/maps/place/Joe%27s+Pizza",
            "description": "Italian restaurant · Call +44 20 7946 0958 · Open now",
        },
        "London, United Kingdom",
        "restaurant",
    )
    assert lead is not None
    assert lead["company_name"]
    assert lead.get("website") is None
    assert "google maps:" in (lead.get("notes") or "").lower()
    assert lead["source"] == "web_search"


def test_map_no_website_from_facebook_page():
    lead = map_no_website_discovery_result(
        {
            "title": "Bella Salon | Facebook",
            "url": "https://www.facebook.com/bellasalonlondon",
            "description": "Hair salon in London. WhatsApp 07700 900123",
        },
        "London, United Kingdom",
        "salon",
    )
    assert lead is not None
    assert lead.get("facebook_url")
    assert lead.get("website") is None
    assert lead["status"] == LeadStatus.new
