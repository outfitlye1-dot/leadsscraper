from app.scrapers.multi_engine_search import (
    parse_brave_results,
    parse_mojeek_results,
    parse_searxng_json,
    parse_yahoo_results,
)


def test_parse_brave_results():
    html = """
    <html><body>
      <div class="snippet" data-type="web">
        <a href="https://acme-plumbing.example.com"><span class="title">Acme Plumbing</span></a>
        <div class="snippet-description"><p>Local plumbers in London</p></div>
      </div>
    </body></html>
    """
    results = parse_brave_results(html)
    assert results
    assert "acme-plumbing.example.com" in results[0]["url"]
    assert "Acme" in results[0]["title"]


def test_parse_yahoo_results():
    html = """
    <html><body>
      <div class="algo">
        <h3><a href="https://bestsalon.example.com">Best Salon</a></h3>
        <p>Hair salon in Berlin</p>
      </div>
    </body></html>
    """
    results = parse_yahoo_results(html)
    assert results
    assert results[0]["url"].startswith("https://bestsalon.example.com")


def test_parse_mojeek_results():
    html = """
    <html><body>
      <ul class="results-standard">
        <li>
          <a class="ob" href="https://cafe.example.org">Local Cafe</a>
          <p class="s">Coffee shop near you</p>
        </li>
      </ul>
    </body></html>
    """
    results = parse_mojeek_results(html)
    assert results
    assert "cafe.example.org" in results[0]["url"]


def test_parse_searxng_json():
    payload = {
        "results": [
            {
                "title": "Green Gym",
                "url": "https://greengym.example.com",
                "content": "Fitness center",
            }
        ]
    }
    results = parse_searxng_json(payload)
    assert len(results) == 1
    assert results[0]["title"] == "Green Gym"


def test_discovery_schedules_extra_engines():
    from app.core.config import get_settings
    from app.scrapers.discovery import SearchDiscovery

    discovery = SearchDiscovery()
    discovery.extra_engines = {"brave", "yahoo", "mojeek"}
    jobs = discovery._engine_jobs("restaurant London", 10, False)
    names = {name for name, _ in jobs}
    assert "bing" in names
    assert "brave" in names
    assert "yahoo" in names
    # Fast mode skips DDGS (hang-prone) and Mojeek (often 403)
    if get_settings().SCRAPER_FAST_MODE:
        assert "ddgs" not in names
        assert "mojeek" not in names
    else:
        assert "ddgs" in names
        assert "mojeek" in names
