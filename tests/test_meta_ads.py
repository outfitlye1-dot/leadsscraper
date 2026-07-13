from app.utils.meta_ads_country import build_ad_library_url, location_to_iso_country
from app.utils.scrape_sources import map_meta_ad_to_lead


def test_location_to_iso_country_germany():
    assert location_to_iso_country("Berlin, Germany") == "DE"


def test_location_to_iso_country_uk():
    assert location_to_iso_country("London, United Kingdom") == "GB"


def test_build_ad_library_url():
    url = build_ad_library_url("wedding planner", "DE")
    assert "country=DE" in url
    assert "wedding" in url.lower()


def test_map_meta_ad_to_lead():
    lead = map_meta_ad_to_lead(
        {
            "company_name": "Bright Studio",
            "website": "https://brightstudio.com",
            "facebook_url": "https://www.facebook.com/brightstudio",
            "ad_text": "We design modern websites",
            "is_active": True,
        },
        "Berlin, Germany",
    )
    assert lead is not None
    assert lead["company_name"] == "Bright Studio"
    assert lead["source"] == "meta_ads"
    assert lead["website"] == "https://brightstudio.com"
    assert "Meta" in (lead.get("notes") or "")


def test_map_meta_ad_skips_facebook_landing():
    lead = map_meta_ad_to_lead(
        {
            "company_name": "Page Only Co",
            "website": "https://facebook.com/somepage",
            "facebook_url": "https://www.facebook.com/somepage",
        },
        "Paris, France",
    )
    assert lead is not None
    assert not lead.get("website")


def test_scraper_start_accepts_meta_ads_source(client, auth_headers):
    response = client.post(
        "/api/scraper/start",
        headers=auth_headers,
        json={
            "keyword": "wedding planner",
            "location": "Berlin, Germany",
            "limit": 5,
            "scrape_source": "meta_ads",
            "include_meta_ads": True,
        },
    )
    assert response.status_code == 200
    assert "job_id" in response.json()
