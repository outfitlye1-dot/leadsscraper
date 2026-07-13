from app.utils.outreach_tone import sanitize_paid_outreach_message, trim_outreach_message


def test_sanitize_removes_free_quote():
    raw = "Hi, would you like a free quote for your website?"
    cleaned = sanitize_paid_outreach_message(raw)
    assert "free" not in cleaned.lower()
    assert "quote" in cleaned.lower()


def test_sanitize_removes_complimentary():
    raw = "We offer a complimentary audit of your online presence."
    cleaned = sanitize_paid_outreach_message(raw)
    assert "free" not in cleaned.lower()
    assert "complimentary" not in cleaned.lower()


def test_trim_outreach_message_at_sentence_boundary():
    long = (
        "Hi Ali, I saw your salon in Lahore. I build websites for local businesses. "
        "Happy to share package details if you are interested in growing online."
    )
    trimmed = trim_outreach_message(long, 90)
    assert len(trimmed) <= 93
    assert trimmed.endswith(".") or trimmed.endswith("...")


def test_build_website_offer_message_no_free():
    from types import SimpleNamespace

    from app.utils.contact_links import build_website_offer_message

    lead = SimpleNamespace(
        contact_name="Ali",
        company_name="Test Salon",
        city="Lahore",
        country="Pakistan",
        category="salon",
        industry=None,
        website=None,
        instagram_url=None,
    )
    msg = build_website_offer_message(lead)
    assert "free" not in msg.lower()
    assert "$300" in msg
    assert "$1,000" in msg or "$1000" in msg
