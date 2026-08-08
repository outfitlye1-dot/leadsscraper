from app.models.lead import Lead, LeadStatus
from app.utils.contact_links import build_contact_links, needs_website_pitch


def _make_lead(**kwargs) -> Lead:
    defaults = {
        "id": 1,
        "user_id": 1,
        "company_name": "Acme Salon",
        "contact_name": "Ali",
        "phone": "+923001234567",
        "email": "info@acme.com",
        "website": None,
        "linkedin_url": "https://linkedin.com/company/acme",
        "instagram_url": None,
        "address": "123 Main St",
        "postal_code": "54000",
        "city": "Lahore",
        "country": "Pakistan",
        "category": "Beauty salon",
        "industry": "Beauty",
        "notes": "",
        "source": "apify",
        "status": LeadStatus.new,
    }
    defaults.update(kwargs)
    return Lead(**defaults)


def test_needs_website_pitch_when_missing_both():
    lead = _make_lead(website=None, instagram_url=None)
    assert needs_website_pitch(lead) is True


def test_contact_links_whatsapp_and_offer():
    lead = _make_lead(
        facebook_url="https://www.facebook.com/acmesalon",
    )
    links = build_contact_links(lead)
    assert links.whatsapp_url is not None
    assert links.email_url is not None
    assert links.linkedin_url is not None
    assert links.facebook_url == "https://www.facebook.com/acmesalon"
    assert links.needs_website_pitch is True
    assert links.website_offer_whatsapp_url is not None
    assert "website" in (links.offer_message or "").lower()
