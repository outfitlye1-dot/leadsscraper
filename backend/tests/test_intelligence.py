from app.services.intelligence.buying_intent_service import calculate_buying_intent
from app.services.intelligence.website_audit_service import audit_website_from_html, audit_website_lightweight


def test_audit_no_website_high_opportunity():
    lead = audit_website_lightweight({"company_name": "ABC Restaurant", "website": None})
    assert lead["website_opportunity_score"] >= 80
    assert "No website" in (lead.get("website_problems") or [])


def test_audit_poor_html_site():
    html = """
    <html><head><title>Old Site</title></head>
    <body><table width="800"><tr><td>Copyright 2015</td></tr></table></body></html>
    """
    lead = audit_website_from_html(
        {"company_name": "Test Co", "website": "http://testco.com"},
        html,
        fetch_ok=True,
    )
    assert lead["website_quality_score"] is not None
    assert lead["website_opportunity_score"] is not None
    problems = lead.get("website_problems") or []
    assert any("HTTPS" in p or "mobile" in p.lower() or "contact" in p.lower() for p in problems)


def test_buying_intent_hot_restaurant_no_site():
    lead = calculate_buying_intent(
        {
            "company_name": "Pizza Planet",
            "category": "restaurant",
            "website": None,
            "facebook_url": "https://facebook.com/pizza",
            "reviews_count": 45,
            "rating": 4.5,
            "phone_verified": True,
        }
    )
    assert lead["buying_intent_score"] >= 70
    assert lead["intent_tier"] == "hot"


def test_buying_intent_penalizes_agency():
    lead = calculate_buying_intent(
        {
            "company_name": "Best Marketing Agency",
            "category": "marketing agency",
            "website": None,
        }
    )
    assert lead["buying_intent_score"] < 60
