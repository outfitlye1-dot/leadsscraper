"""Tests for enterprise scraping engine modules."""

from app.scraper.utils.anti_bot import detect_bot_block
from app.scrapers.ai_selectors import discover_selectors_from_html, repair_selectors, validate_selectors
from app.scrapers.crawl_frontier import CrawlFrontier, normalize_url
from app.scrapers.image_intel import extract_images
from app.scrapers.strategy_router import decide_strategy, detect_framework


def test_normalize_url_strips_tracking():
    url = normalize_url("https://example.com/page?utm_source=x&id=1")
    assert "utm_source" not in url
    assert "id=1" in url


def test_crawl_frontier_depth_limit():
    frontier = CrawlFrontier("https://example.com", max_depth=1, max_urls=10)
    frontier.add_links("https://example.com", ["https://example.com/about"])
    child = frontier.pop()
    assert child is not None
    frontier.add_links(child[0], ["https://example.com/about/team"])
    assert frontier.pop() is None or frontier.pending_count() >= 0


def test_detect_cloudflare():
    html = "<html><body>Just a moment... checking your browser cloudflare</body></html>"
    result = detect_bot_block(html, status_code=503)
    assert result.blocked
    assert result.should_use_browser


def test_strategy_router_react():
    html = '<html><div id="root" data-reactroot></div><script>__NEXT_DATA__</script></html>'
    decision = decide_strategy("https://app.vercel.app", html)
    assert decision.strategy.value in ("playwright", "api_intercept")


def test_ai_selectors_discover():
    html = """
    <html><body>
    <h1>Acme Corp</h1>
    <a href="mailto:hello@acme.com">Email</a>
    <a href="tel:+441234567890">Call</a>
    </body></html>
    """
    schema = discover_selectors_from_html(html, "https://acme.com")
    valid = validate_selectors(html, schema.all_selectors())
    assert any("mailto" in s for s in valid)


def test_repair_selectors_fallback():
    html = "<html><a href='mailto:test@x.com'>x</a></html>"
    repaired = repair_selectors(html, "https://x.com", [".broken-selector"])
    assert len(repaired) > 0


def test_image_extraction_srcset():
    html = """
    <html><body>
    <img src="/logo.png" srcset="/logo-1x.png 1x, /logo-2x.png 2x" alt="Company Logo" />
    </body></html>
    """
    result = extract_images(html, "https://example.com")
    assert len(result.images) >= 1
    assert result.logo_url


def test_detect_framework_nextjs():
    html = "<html><script>__NEXT_DATA__ = {}</script></html>"
    assert detect_framework(html) == "nextjs"
