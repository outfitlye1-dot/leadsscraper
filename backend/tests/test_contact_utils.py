from app.utils.contact_utils import (
    build_whatsapp_link,
    extract_emails_from_text,
    extract_phones_from_text,
    is_junk_email,
    is_valid_email,
    is_whatsapp_ready,
    normalize_whatsapp_phone,
    pick_best_email,
    score_email,
)


def test_is_valid_email():
    assert is_valid_email("hello@company.com")
    assert is_valid_email("info@acmeagency.com")
    assert not is_valid_email("not-an-email")
    assert not is_valid_email(None)
    assert not is_valid_email("test@example.com")
    assert not is_valid_email("noreply@company.com")


def test_is_junk_email():
    assert is_junk_email("fake@example.com")
    assert not is_junk_email("sales@realbusiness.com")
    assert is_junk_email("2a0e6f82eb8f46caa125cd68ecf0c94c@sentry.freeola.systems")
    assert is_junk_email("alert@sentry.freeola.systems")


def test_normalize_whatsapp_phone_pakistan():
    assert normalize_whatsapp_phone("03001234567", "Pakistan") == "923001234567"
    assert normalize_whatsapp_phone("+923001234567", "Pakistan") == "923001234567"
    assert normalize_whatsapp_phone("0300-1234567", "Pakistan") == "923001234567"
    assert normalize_whatsapp_phone("300 1234567", "Pakistan") == "923001234567"
    assert normalize_whatsapp_phone("02134567890", "Pakistan") is None
    assert normalize_whatsapp_phone("1111111111", "Pakistan") is None
    assert normalize_whatsapp_phone("2024-2025", "Pakistan") is None


def test_normalize_whatsapp_phone_uae():
    assert normalize_whatsapp_phone("0501234567", "UAE") == "971501234567"
    assert normalize_whatsapp_phone("+971501234567", "UAE") == "971501234567"


def test_extract_phone_from_whatsapp_href():
    from app.utils.contact_utils import extract_phone_from_whatsapp_href

    assert extract_phone_from_whatsapp_href("https://wa.me/923001234567") == "923001234567"
    assert extract_phone_from_whatsapp_href("https://api.whatsapp.com/send?phone=923001234567&text=Hi") == "923001234567"


def test_rejects_invalid_whatsapp_formats():
    assert normalize_whatsapp_phone("12345", "Pakistan") is None
    assert normalize_whatsapp_phone("021-34567890", "Pakistan") is None


def test_is_whatsapp_ready():
    assert is_whatsapp_ready("+923001234567", "Pakistan")
    assert not is_whatsapp_ready("123", "Pakistan")
    assert not is_whatsapp_ready("02134567890", "Pakistan")


def test_extract_emails_from_text():
    text = "Contact us at info@acme.com or bad@image.png or test@example.com"
    emails = extract_emails_from_text(text, "https://acme.com")
    assert emails[0] == "info@acme.com"
    assert "test@example.com" not in emails


def test_pick_best_email_prefers_domain_match():
    emails = ["hello@gmail.com", "info@acme.com"]
    best = pick_best_email(emails, "https://www.acme.com")
    assert best == "info@acme.com"


def test_score_email_domain_match():
    assert score_email("info@acme.com", "https://acme.com") > score_email(
        "hello@gmail.com", "https://acme.com"
    )


def test_extract_phones_wa_me():
    text = 'Chat on <a href="https://wa.me/923001234567">WhatsApp</a>'
    phones = extract_phones_from_text(text, "Pakistan")
    assert any("923001234567" in p.replace("+", "") for p in phones)


def test_wa_me_with_wrong_search_country():
    """PK number from wa.me must validate even if search location says UK."""
    assert normalize_whatsapp_phone("923001234567", "United Kingdom", from_whatsapp_link=True) == "923001234567"
    assert is_whatsapp_ready("+923001234567", "United Kingdom")


def test_web_whatsapp_send_link():
    from app.utils.contact_utils import extract_phone_from_whatsapp_href

    href = "https://web.whatsapp.com/send?phone=923331234567&text=Hello"
    assert extract_phone_from_whatsapp_href(href) == "923331234567"


def test_extract_obfuscated_email():
    from app.utils.contact_utils import extract_emails_from_text

    text = "Reach us at hello [at] acmeagency.com for quotes"
    emails = extract_emails_from_text(text, "https://acmeagency.com")
    assert emails and emails[0] == "hello@acmeagency.com"


def test_build_whatsapp_link():
    link = build_whatsapp_link("923001234567", "Hello there")
    assert link.startswith("https://wa.me/923001234567")
    assert "Hello" in link


def test_format_contact_phone_keeps_landline():
    from app.utils.contact_utils import format_contact_phone

    assert format_contact_phone("020 7946 0958", "United Kingdom") == "+442079460958"
    assert format_contact_phone("03001234567", "Pakistan") == "+923001234567"


def test_sanitize_lead_contacts_keeps_maps_landline():
    from app.utils.lead_contacts import sanitize_lead_contacts

    lead = {
        "company_name": "London Cafe",
        "phone": "020 7946 0958",
        "country": "United Kingdom",
        "source": "apify",
    }
    cleaned = sanitize_lead_contacts(lead, search_location="London, United Kingdom")
    assert cleaned.get("phone") == "+442079460958"
