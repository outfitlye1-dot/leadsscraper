from app.utils.scrape_defaults import (
    DEFAULT_SCRAPE_LOCATION,
    is_europe_target,
    normalize_location_alias,
    resolve_scrape_location,
)


def test_default_location_is_europe():
    assert "United Kingdom" in DEFAULT_SCRAPE_LOCATION


def test_resolve_empty_to_london():
    assert resolve_scrape_location("") == DEFAULT_SCRAPE_LOCATION
    assert resolve_scrape_location("Global") == DEFAULT_SCRAPE_LOCATION


def test_normalize_europe_aliases():
    assert normalize_location_alias("germany") == "Berlin, Germany"
    assert normalize_location_alias("london") == "London, United Kingdom"
    assert normalize_location_alias("Berlin, Germany") == "Berlin, Germany"


def test_is_europe_target():
    assert is_europe_target("London, United Kingdom")
    assert is_europe_target("Paris, France")
    assert not is_europe_target("Karachi, Pakistan")
