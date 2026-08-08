"""Smoke tests for authenticated API routes (no live scraping)."""

import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/dashboard/stats"),
        ("GET", "/api/leads"),
        ("GET", "/api/leads?saved=true"),
        ("GET", "/api/messages"),
        ("GET", "/api/campaigns"),
        ("GET", "/api/brain"),
        ("GET", "/api/scraper/daily/status"),
        ("GET", "/api/scraper/active"),
        ("GET", "/api/scraper/auto/status"),
        ("GET", "/api/scraper/background/status"),
    ],
)
def test_authenticated_get_endpoints_return_ok(client, auth_headers, method, path):
    response = client.request(method, path, headers=auth_headers)
    assert response.status_code == 200, f"{method} {path} -> {response.status_code}: {response.text[:200]}"


def test_health_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_unauthenticated_protected_route_returns_401(client):
    response = client.get("/api/leads")
    assert response.status_code == 401


def test_scraper_start_validation_error(client, auth_headers):
    response = client.post(
        "/api/scraper/start",
        headers=auth_headers,
        json={"keyword": "", "location": "", "scrape_source": "google_search", "limit": 10},
    )
    assert response.status_code == 422
