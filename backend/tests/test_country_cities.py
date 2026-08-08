from app.utils.scrape_defaults import (
    cities_for_country,
    list_scrape_countries,
    normalize_country_name,
)


def test_normalize_country_aliases():
    assert normalize_country_name("UK") == "United Kingdom"
    assert normalize_country_name("pakistan") == "Pakistan"
    assert normalize_country_name("United Kingdom") == "United Kingdom"
    assert normalize_country_name("nowhere") is None


def test_cities_for_country_format():
    cities = cities_for_country("UK")
    assert len(cities) >= 5
    assert cities[0] == "London, United Kingdom"
    assert all(", United Kingdom" in c for c in cities)


def test_list_scrape_countries_includes_uk():
    countries = list_scrape_countries()
    assert "United Kingdom" in countries
    assert "Pakistan" in countries
