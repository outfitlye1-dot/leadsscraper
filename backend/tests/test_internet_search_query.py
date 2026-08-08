from app.schemas.common import ScraperStartRequest
from app.utils.scrape_sources import ScrapeSourceMode, build_internet_search_query
from app.scrapers.discovery import SearchDiscovery
from app.utils.website_utils import WebsiteFilter


def test_build_internet_search_query_from_keyword_location():
    q = build_internet_search_query("restaurant", "London, UK")
    assert "restaurant" in q
    assert "London" in q
    # Keep short — stacked contact words empty DDGS
    assert "whatsapp" not in q.lower()


def test_scraper_request_auto_fills_internet_query():
    req = ScraperStartRequest(
        keyword="salon",
        location="Berlin, Germany",
        scrape_source=ScrapeSourceMode.google_search,
        website_filter=WebsiteFilter.all,
        limit=10,
    )
    assert req.search_query
    assert "salon" in req.search_query
    assert "Berlin" in req.search_query
    assert req.website_filter == WebsiteFilter.all


def test_discovery_builds_short_queries_from_keyword():
    discovery = SearchDiscovery()
    queries = discovery._build_queries("plumber", "Paris, France", limit=20, search_query=None)
    assert queries
    joined = " ".join(queries).lower()
    assert "plumber" in joined
    assert "paris" in joined
    assert any(q.lower() == "plumber paris, france" or "plumber paris" in q.lower() for q in queries)
