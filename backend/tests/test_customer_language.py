"""Country → customer language for Brain outreach."""

from app.utils.customer_language import language_rules_for_country, resolve_customer_language


def test_pakistan_uses_roman_urdu():
    lang, _ = resolve_customer_language("Pakistan")
    assert "Urdu" in lang
    block = language_rules_for_country("Pakistan", "Karachi")
    assert "Urdu" in block
    assert "Karachi" in block


def test_germany_uses_german():
    lang, _ = resolve_customer_language("Germany")
    assert lang.startswith("German")


def test_unknown_falls_back_to_english():
    lang, _ = resolve_customer_language("Atlantis")
    assert lang.startswith("English")


def test_city_country_string_parsed():
    lang, _ = resolve_customer_language("Lahore, Pakistan")
    assert "Urdu" in lang
