from app.services.web_search_service import _prioritize_discovery


def test_prioritize_discovery_puts_contact_rich_results_first():
    items = [
        {"title": "Generic Agency", "url": "https://a.com", "description": "Web design services"},
        {
            "title": "Beta Studio",
            "url": "https://b.com",
            "description": "Email hello@beta.com or WhatsApp 03001234567",
        },
        {"title": "Gamma Co", "url": "https://c.com", "description": "Call us today"},
    ]
    ordered = _prioritize_discovery(items)
    assert ordered[0]["url"] == "https://b.com"
