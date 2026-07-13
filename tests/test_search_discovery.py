from unittest.mock import MagicMock, patch

from app.scrapers.discovery import SearchDiscovery


def test_search_discovery_with_query():
    discovery = SearchDiscovery()
    with (
        patch.object(discovery, "_search_ddgs") as mock_ddgs_search,
        patch.object(discovery, "_search_bing", return_value=[]),
        patch.object(discovery, "_search_ddg_html", return_value=[]),
    ):
        mock_ddgs_search.return_value = [
            {
                "title": "Acme Agency",
                "url": "https://acmeagency.com",
                "description": "Web design",
            }
        ]
        results = discovery.search(
            search_query="web design agency Karachi Pakistan", limit=5
        )

    assert len(results) == 1
    assert results[0]["url"] == "https://acmeagency.com"
    assert mock_ddgs_search.call_count == 3


def test_ddg_html_retries_on_http_error():
    discovery = SearchDiscovery()
    discovery.retries = 2
    mock_response = MagicMock()
    mock_response.status_code = 503
    with patch.object(discovery._session, "post", return_value=mock_response) as mock_post:
        results = discovery._search_ddg_html("test query")
    assert results == []
    assert mock_post.call_count == 2
