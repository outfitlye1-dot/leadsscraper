from app.utils.phone_confidence import PhoneHit, aggregate_phone_hits, score_phone_hit
from app.utils.phone_extract import extract_phones_from_html, pick_verified_phone_from_html


def test_wa_me_link_uk():
    html = '<html><body><a href="https://wa.me/447911123456">WhatsApp</a></body></html>'
    phone = pick_verified_phone_from_html(html, "United Kingdom")
    assert phone is not None
    assert "447911123456" in phone.replace("+", "").replace(" ", "")


def test_tel_link_germany():
    html = '<html><body><a href="tel:+491701234567">Call</a></body></html>'
    phone = pick_verified_phone_from_html(html, "Germany")
    assert phone is not None
    digits = "".join(c for c in phone if c.isdigit())
    assert "491701234567" in digits or digits.endswith("1701234567")


def test_data_whatsapp_widget():
    html = '<div class="whatsapp-widget" data-href="https://wa.me/33612345678"></div>'
    phone = pick_verified_phone_from_html(html, "France")
    assert phone is not None


def test_itemprop_telephone():
    html = '<span itemprop="telephone">+33 6 12 34 56 78</span>'
    phone = pick_verified_phone_from_html(html, "France")
    assert phone is not None


def test_wa_me_anchor_netherlands():
    html = """<a href="https://wa.me/31612345678">Chat on WhatsApp</a>"""
    phone = pick_verified_phone_from_html(html, "Netherlands")
    assert phone is not None


def test_multi_region_plain_text_uk():
    html = "<html><body>Call us on 07911 123456 for support.</body></html>"
    phone = pick_verified_phone_from_html(html, "United Kingdom")
    assert phone is not None


def test_rejects_random_us_number_on_uk_page():
    html = "<html><body>Partner office: +1 202 555 0199</body></html>"
    phone = pick_verified_phone_from_html(html, "United Kingdom")
    assert phone is None


def test_consensus_two_pages_same_number():
    html1 = '<a href="tel:07911123456">Call</a>'
    html2 = "<p>Phone: 07911 123456</p>"
    hits = []
    from app.utils.phone_extract import extract_phone_hits_from_html

    hits.extend(extract_phone_hits_from_html(html1, "United Kingdom"))
    hits.extend(extract_phone_hits_from_html(html2, "United Kingdom"))
    phone = aggregate_phone_hits(hits, "United Kingdom")
    assert phone is not None
