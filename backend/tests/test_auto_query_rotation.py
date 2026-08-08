from app.schemas.common import ScraperStartRequest
from app.utils.auto_query_rotation import (
    build_auto_scrape_variants,
    keyword_rotation_pool,
    lock_auto_internet_only,
    pick_auto_scrape_request,
    pick_rotated_keyword,
    prepare_auto_scrape_base,
)
from app.utils.scrape_sources import ScrapeSourceMode


def test_lock_auto_keeps_selected_source():
    base = ScraperStartRequest(
        keyword="restaurant",
        location="London, United Kingdom",
        search_query="restaurant London contact email",
        limit=10,
        scrape_source=ScrapeSourceMode.google_maps,
        include_meta_ads=True,
    )

    locked = lock_auto_internet_only(base)

    assert locked.scrape_source == ScrapeSourceMode.google_maps
    assert locked.include_meta_ads is False


def test_prepare_auto_scrape_keeps_selected_source():
    base = ScraperStartRequest(
        keyword="restaurant",
        location="London, United Kingdom",
        limit=10,
        scrape_source=ScrapeSourceMode.google_maps,
    )

    prepared = prepare_auto_scrape_base(base)

    assert prepared.scrape_source == ScrapeSourceMode.google_maps
    assert prepared.include_meta_ads is False
    assert prepared.website_filter.value == "all"
    assert prepared.enrich_contacts is True
    assert "restaurant" in prepared.search_query.lower()
    assert "London" in prepared.search_query
    # Keep queries short — no stacked contact spam
    assert prepared.search_query.lower().count("contact") <= 1
    assert "whatsapp phone number" not in prepared.search_query.lower()


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
    """Background runner must not construct empty keyword queries."""
    from app.utils.scrape_defaults import DEFAULT_SCRAPE_LOCATION

    base = ScraperStartRequest(
        keyword="restaurant",
        location=DEFAULT_SCRAPE_LOCATION,
        limit=25,
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


def test_auto_scrape_pool_keeps_selected_source():
    base = ScraperStartRequest(
        keyword="restaurant",
        location="London, United Kingdom",
        search_query="restaurant London contact email",
        limit=10,
        scrape_source=ScrapeSourceMode.google_maps,
    )

    pool = build_auto_scrape_variants(base, None)

    assert len(pool) >= 3
    assert all(item.scrape_source == ScrapeSourceMode.google_maps for item in pool)
    assert all(item.search_query for item in pool)
    # Queries should stay short enough for DDGS
    assert all(len(item.search_query or "") < 120 for item in pool)


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

    assert any("lahore" in q for q in queries) or any(
        "lahore" in (item.location or "").lower() for item in pool
    )


def test_keyword_rotation_pool_rotates_distinct_keywords():
    pool = keyword_rotation_pool("plumber")
    assert pool[0] == "plumber"
    assert len(pool) >= 3

    a = pick_rotated_keyword(pool, 0)
    b = pick_rotated_keyword(pool, 1)
    c = pick_rotated_keyword(pool, len(pool))
    assert a == "plumber"
    assert b != a or len(pool) == 1
    assert c == pool[0]


def test_keyword_rotation_pool_can_lock_single_keyword():
    pool = keyword_rotation_pool("plumber", rotate=False)
    assert pool == ["plumber"]


def test_auto_variants_lock_keyword_when_rotate_off():
    from app.schemas.common import ScraperStartRequest

    base = ScraperStartRequest(
        keyword="cafe",
        location="London, United Kingdom",
        limit=10,
        rotate_keywords=False,
        scrape_source="google_maps",
    )
    pool = build_auto_scrape_variants(base, None)
    assert pool
    assert all((v.keyword or "").strip().lower() == "cafe" for v in pool)
