from app.scrapers.parser import extract_contacts_from_html, parse_duckduckgo_results


def test_parse_duckduckgo_results():
    html = """
    <div class="result">
      <a class="result__a" href="https://acme.com">Acme Agency</a>
      <a class="result__snippet">Web design company</a>
    </div>
    """
    results = parse_duckduckgo_results(html)
    assert len(results) == 1
    assert results[0]["url"] == "https://acme.com"
    assert results[0]["title"] == "Acme Agency"


def test_extract_contacts_from_html():
    html = """
    <html>
      <head><title>Acme Agency</title></head>
      <body>
        <a href="mailto:hello@acme.com">Email us</a>
        <a href="tel:+923001234567">Call</a>
        <a href="https://linkedin.com/company/acme">LinkedIn</a>
      </body>
    </html>
    """
    contacts = extract_contacts_from_html(html, "https://acme.com", "Pakistan")
    assert contacts["email"] == "hello@acme.com"
    assert contacts["phone"] == "+923001234567"
    assert "linkedin.com" in (contacts["linkedin_url"] or "")
