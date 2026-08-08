from unittest.mock import MagicMock

from app.scrapers.crawler_core import scrape_business_site


def test_scrape_business_site():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = (
        """
        <html><head><title>Acme Agency</title></head>
        <body><a href="mailto:info@acme.com">Email</a></body></html>
        """,
        "https://acme.com",
    )

    result = scrape_business_site(
        mock_fetcher, "https://acme.com", "Acme Agency", "Karachi, Pakistan"
    )
    assert result is not None
    assert result["company_name"] == "Acme Agency"
    assert result["email"] == "info@acme.com"


def test_scrape_business_site_extracts_wa_me_phone():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = (
        """
        <html><head><title>London Plumbing Ltd</title></head>
        <body>
          <a href="https://wa.me/447911123456">WhatsApp us</a>
        </body></html>
        """,
        "https://londonplumbing.co.uk",
    )

    result = scrape_business_site(
        mock_fetcher,
        "https://londonplumbing.co.uk",
        "London Plumbing Ltd",
        "London, United Kingdom",
    )
    assert result is not None
    assert result.get("phone")
    digits = "".join(c for c in result["phone"] if c.isdigit())
    assert "447911123456" in digits


def test_scrape_business_site_prefers_hostname_over_long_seo_title():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = (
        """
        <html><head>
          <title>Mobit Solutions Presents Cost Effective IT Solutions</title>
          <meta property="og:site_name" content="Mobit Solutions" />
        </head>
        <body><a href="mailto:dee@mobitsolutions.com">Email</a></body></html>
        """,
        "https://www.mobitsolutions.com/uk/web-development-company-uk/",
    )

    result = scrape_business_site(
        mock_fetcher,
        "https://www.mobitsolutions.com/uk/web-development-company-uk/",
        "Mobit Solutions Presents Cost Effective IT Solutions",
        "London, United Kingdom",
    )
    assert result is not None
    assert result["company_name"] == "Mobit Solutions"
