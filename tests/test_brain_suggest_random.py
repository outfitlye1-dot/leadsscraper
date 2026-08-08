from app.utils.auto_query_rotation import pick_fresh_brain_suggestion
from app.utils.scrape_suggest import suggest_scrape_from_profile_rules


def test_pick_fresh_brain_suggestion_avoids_current_keyword():
    base = suggest_scrape_from_profile_rules({}, "google_search")
    current = base["recommended_keyword"]

    seen: set[str] = {current.lower()}
    for _ in range(12):
        fresh = pick_fresh_brain_suggestion(
            base,
            profile=None,
            scrape_source="google_search",
            current_keyword=current,
            current_search_query=base["recommended_search_query"],
            location="London, UK",
        )
        kw = fresh["recommended_keyword"].strip().lower()
        assert kw != current.lower()
        assert fresh["recommended_search_query"].strip()
        current = fresh["recommended_keyword"]
        seen.add(kw)

    assert len(seen) >= 3
