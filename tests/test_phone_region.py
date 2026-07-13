from app.utils.phone_lib import phone_matches_search_region


def test_phone_matches_uk_search():
    assert phone_matches_search_region("+447380284498", "London, United Kingdom")
    assert not phone_matches_search_region("+919106686124", "London, United Kingdom")
    assert not phone_matches_search_region("+923214191446", "London, United Kingdom")


def test_phone_matches_when_location_unknown():
    assert phone_matches_search_region("+919106686124", None)
    assert phone_matches_search_region("+919106686124", "")
