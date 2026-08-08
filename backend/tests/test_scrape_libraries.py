from app.utils.phone_lib import normalize_whatsapp_e164, is_whatsapp_mobile


def test_phone_lib_pakistan():
    assert normalize_whatsapp_e164("0300-1234567", "Pakistan") == "+923001234567"
    assert normalize_whatsapp_e164("+923001234567", "Pakistan") == "+923001234567"
    assert normalize_whatsapp_e164("021-34567890", "Pakistan") is None
    assert is_whatsapp_mobile("03001234567", "Pakistan")


def test_phone_lib_uae():
    assert normalize_whatsapp_e164("050 123 4567", "UAE") == "+971501234567"


def test_structured_extract_json_ld():
    from app.scrapers.structured_extract import extract_structured_business

    html = """
    <html><head>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Restaurant",
      "name": "Pizza Planet",
      "telephone": "+923001234567",
      "email": "info@pizzaplanet.com"
    }
    </script>
    </head><body></body></html>
    """
    data = extract_structured_business(html, "https://pizzaplanet.com")
    assert data["name"] == "Pizza Planet"
    assert data["telephone"] == "+923001234567"
    assert data["category"] == "Restaurant"
    assert data["email"] == "info@pizzaplanet.com"
