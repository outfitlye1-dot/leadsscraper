from app.utils.website_utils import (
    WebsiteFilter,
    apply_website_filter,
    has_real_website,
    is_google_maps_url,
    normalize_website_field,
)


def test_is_google_maps_url():
    assert is_google_maps_url("https://www.google.com/maps/place/Test")
    assert not is_google_maps_url("https://acme.com")


def test_has_real_website():
    assert has_real_website("https://acme.com")
    assert not has_real_website("https://facebook.com/acme")
    assert not has_real_website(None)


def test_normalize_maps_url_not_website():
    lead = normalize_website_field(
        {
            "company_name": "Test Shop",
            "website": "https://www.google.com/maps/place/Test+Shop",
            "notes": "A shop",
        }
    )
    assert lead["website"] is None
    assert "Website: No" in lead["notes"]


def test_normalize_real_website():
    lead = normalize_website_field(
        {"company_name": "Acme", "website": "https://www.acme.com", "notes": ""}
    )
    assert lead["website"] == "https://www.acme.com"
    assert "Website: Yes" in lead["notes"]


def test_apply_website_filter():
    leads = [
        {"company_name": "A", "website": "https://a.com"},
        {"company_name": "B", "website": None},
    ]
    with_site = apply_website_filter(leads, WebsiteFilter.with_website)
    without = apply_website_filter(leads, WebsiteFilter.without_website)
    assert len(with_site) == 1
    assert len(without) == 1
    assert with_site[0]["company_name"] == "A"
    assert without[0]["company_name"] == "B"
