from app.utils.contact_utils import pick_best_phone, score_phone
from app.utils.phone_confidence import PhoneHit, score_phone_hit


def test_pick_best_phone_prefers_country_match():
    phones = ["+12025550199", "+447911123456"]
    best = pick_best_phone(phones, "United Kingdom")
    assert best is not None
    assert "447911123456" in best.replace("+", "")


def test_score_penalizes_country_mismatch():
    uk_score = score_phone("+447911123456", "United Kingdom")
    us_score = score_phone("+12025550199", "United Kingdom")
    assert uk_score > us_score


def test_wa_me_pk_number_ok_with_uk_search():
    hit = PhoneHit(raw="923001234567", source="wa_me", country="United Kingdom", from_whatsapp=True)
    assert score_phone_hit(hit, "United Kingdom") >= 70


def test_low_confidence_pattern_rejected_alone():
    hit = PhoneHit(raw="+12025550199", source="libphonenumber", country="United Kingdom")
    from app.utils.phone_confidence import aggregate_phone_hits

    assert aggregate_phone_hits([hit], "United Kingdom") is None
