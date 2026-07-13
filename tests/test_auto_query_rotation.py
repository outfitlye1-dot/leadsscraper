from app.schemas.common import ScraperStartRequest
from app.utils.auto_query_rotation import (
    build_auto_scrape_variants,
    lock_auto_internet_only,
    pick_auto_scrape_request,
    prepare_auto_scrape_base,
)
from app.utils.scrape_sources import ScrapeSourceMode


def test_lock_auto_internet_only_overrides_maps():
    base = ScraperStartRequest(
        keyword="restaurant",
        location="London, United Kingdom",
        search_query="restaurant London contact email",
        limit=10,
        scrape_source=ScrapeSourceMode.google_maps,
        include_meta_ads=True,
    )

    locked = lock_auto_internet_only(base)

    assert locked.scrape_source == ScrapeSourceMode.google_search
    assert locked.include_meta_ads is False


def test_prepare_auto_scrape_forces_internet_only():
    base = ScraperStartRequest(
        keyword="restaurant",
        location="London, United Kingdom",
        limit=10,
        scrape_source=ScrapeSourceMode.google_maps,
    )

    prepared = prepare_auto_scrape_base(base)

    assert prepared.scrape_source == ScrapeSourceMode.google_search
    assert prepared.include_meta_ads is False
    assert prepared.website_filter.value == "all"
    assert prepared.enrich_contacts is True
    assert "restaurant" in prepared.search_query
    assert "London" in prepared.search_query


def test_prepare_auto_scrape_uses_brain_profile():
    profile = {
        "name": "Ali",
        "services": ["web design"],
        "custom_notes": "Lahore, Pakistan",
    }
    base = ScraperStartRequest(
        keyword="restaurant",
        location="Lahore, Pakistan",
        search_query="restaurant Lahore contact email",
        limit=10,
        scrape_source=ScrapeSourceMode.google_search,
    )

    prepared = prepare_auto_scrape_base(base, profile)

    assert prepared.search_query
    assert "Lahore" in prepared.location or "Pakistan" in prepared.location


def test_prepare_auto_scrape_fills_empty_keyword():
    base = ScraperStartRequest(
        keyword="",
        location="London, United Kingdom",
        search_query="local business London contact email phone",
        limit=10,
        scrape_source=ScrapeSourceMode.google_search,
    )

    prepared = prepare_auto_scrape_base(base)

    assert prepared.keyword.strip()
    assert prepared.location.strip()
    assert prepared.search_query
    assert prepared.scrape_source == ScrapeSourceMode.google_search


def test_background_base_request_validates():
    """Background runner must not construct google_search with empty keyword."""
    from app.utils.scrape_defaults import DEFAULT_SCRAPE_LOCATION
    from app.utils.website_utils import WebsiteFilter

    base = ScraperStartRequest(
        keyword="restaurant",
        location=DEFAULT_SCRAPE_LOCATION,
        limit=25,
        website_filter=WebsiteFilter.all,
    )
    prepared = prepare_auto_scrape_base(base)
    chosen, _ = pick_auto_scrape_request(prepared, None, 1)

    assert chosen.keyword.strip()
    assert chosen.location.strip()
    assert chosen.search_query


def test_background_scrape_rotates_keyword_location_each_round():
    from app.utils.auto_query_rotation import pick_background_scrape_request

    base = ScraperStartRequest(
        keyword="restaurant",
        location="London, United Kingdom",
        limit=25,
    )

    first, label1 = pick_background_scrape_request(base, None, 1)
    second, label2 = pick_background_scrape_request(base, None, 2)
    third, _ = pick_background_scrape_request(base, None, 3)

    assert first.keyword.strip()
    assert first.location.strip()
    assert first.search_query
    assert second.keyword != first.keyword or second.location != first.location
    assert second.search_query != first.search_query
    assert third.search_query != second.search_query
    assert " — " in label1


def test_auto_scrape_rotates_search_query_each_round():
    base = ScraperStartRequest(
        keyword="",
        location="London, United Kingdom",
        search_query="web design agency London contact email",
        limit=10,
        scrape_source=ScrapeSourceMode.google_search,
    )

    first, label1 = pick_auto_scrape_request(base, None, 1)
    second, label2 = pick_auto_scrape_request(base, None, 2)

    assert first.search_query
    assert second.search_query
    assert first.search_query != second.search_query or label1 != label2


def test_auto_scrape_pool_is_internet_only():
    base = ScraperStartRequest(
        keyword="restaurant",
        location="London, United Kingdom",
        search_query="restaurant London contact email",
        limit=10,
        scrape_source=ScrapeSourceMode.google_maps,
    )

    pool = build_auto_scrape_variants(base, None)

    assert len(pool) >= 3
    assert all(item.scrape_source == ScrapeSourceMode.google_search for item in pool)
    assert all(item.search_query for item in pool)


def test_auto_scrape_uses_brain_suggestions_in_pool():
    profile = {
        "name": "Ali",
        "services": ["web design"],
        "custom_notes": "Lahore, Pakistan",
    }
    base = ScraperStartRequest(
        keyword="",
        location="Lahore, Pakistan",
        search_query="web design agency Lahore contact email",
        limit=10,
        scrape_source=ScrapeSourceMode.google_search,
    )

    pool = build_auto_scrape_variants(base, profile)
    queries = {item.search_query.lower() for item in pool if item.search_query}

    assert any("lahore" in q for q in queries)
    assert any("contact" in q or "whatsapp" in q or "phone" in q for q in queries)
