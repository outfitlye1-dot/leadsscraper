from app.utils.query_optimizer import optimize_search_query_rules


def test_optimize_search_query_rules_adds_contact():
    result = optimize_search_query_rules("web design karachi")
    assert "contact" in result["optimized_query"].lower()
    assert len(result["suggestions"]) >= 2
    assert result["was_corrected"] is True


def test_optimize_search_query_rules_defaults_to_europe():
    result = optimize_search_query_rules("web design agency")
    assert "United Kingdom" in result["optimized_query"] or "London" in result["optimized_query"]
    assert "Pakistan" not in result["optimized_query"]


def test_optimize_search_query_rules_good_query():
    query = "web design agency Karachi Pakistan contact email"
    result = optimize_search_query_rules(query)
    assert result["optimized_query"]
    assert result["was_corrected"] is False


def test_optimize_search_query_rules_uses_form_location():
    result = optimize_search_query_rules("restaurant", location="Berlin, Germany")
    assert "berlin" in result["optimized_query"].lower()
    assert "germany" in result["optimized_query"].lower()
