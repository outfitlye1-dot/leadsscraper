from app.schemas.common import ScraperStartRequest
from app.utils.scrape_sources import ScrapeSourceMode, build_internet_search_query
from app.scrapers.discovery import SearchDiscovery


def test_build_internet_search_query_from_keyword_location():
    q = build_internet_search_query("restaurant", "London, UK")
    assert "restaurant" in q
    assert "London" in q
    assert "contact" in q


def test_scraper_request_auto_fills_internet_query():
    req = ScraperStartRequest(
        keyword="salon",
        location="Berlin, Germany",
        scrape_source=ScrapeSourceMode.google_search,
        limit=10,
    )
    assert req.search_query
    assert "salon" in req.search_query
    assert "Berlin" in req.search_query


def test_discovery_builds_maps_style_queries_from_keyword():
    discovery = SearchDiscovery()
    queries = discovery._build_queries("plumber", "Paris, France", limit=20, search_query=None)
    assert queries
    joined = " ".join(queries).lower()
    assert "plumber" in joined
    assert "paris" in joined
    assert "google maps" in joined
