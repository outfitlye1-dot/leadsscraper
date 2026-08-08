from types import SimpleNamespace

from app.services.intelligence.advanced_dedup import is_fuzzy_duplicate, mark_batch_duplicates
from app.services.intelligence.contact_verification_service import verify_lead_contacts
from app.services.intelligence.niche_intelligence import apply_niche_intelligence, detect_niche


def test_detect_niche_restaurant():
    assert detect_niche({"company_name": "Pizza Planet", "category": "restaurant"}) == "restaurant"


def test_apply_niche_adds_pain_points():
    lead = apply_niche_intelligence(
        {"company_name": "Glow Salon", "category": "beauty salon", "website_problems": []}
    )
    assert lead["niche_key"] == "salon"
    assert lead.get("recommended_service")
    assert lead.get("website_problems")


def test_fuzzy_duplicate_by_name_and_city():
    existing = SimpleNamespace(company_name="Acme Salon", city="Lahore", address=None)
    lead = {"company_name": "Acme Salon", "city": "Lahore", "phone": "+923009999999"}
    assert is_fuzzy_duplicate(lead, existing)


def test_mark_batch_duplicates_removes_phone_dup():
    existing = [
        SimpleNamespace(
            company_name="Old Co",
            phone="+923001234567",
            email=None,
            website="https://old.com",
            country="Pakistan",
            city="Lahore",
            address=None,
        )
    ]
    batch = [
        {"company_name": "Old Co", "phone": "+923001234567", "website": "https://old.com", "country": "Pakistan"},
        {"company_name": "New Co", "phone": "+923009999999", "website": "https://new.com", "country": "Pakistan"},
    ]
    unique, removed = mark_batch_duplicates(batch, existing)
    assert removed == 1
    assert len(unique) == 1


def test_verify_lead_contacts_email():
    lead = verify_lead_contacts(
        {"email": "info@company.com", "website": "https://company.com", "country": "Pakistan"},
        "Pakistan",
    )
    assert lead.get("email_verified") is True
