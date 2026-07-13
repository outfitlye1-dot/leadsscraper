"""Live API smoke test against running backend (optional manual run)."""

import os
import uuid

import httpx
import pytest

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")


@pytest.fixture(scope="module")
def live_token():
    email = f"autotest_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    with httpx.Client(base_url=BASE, timeout=10.0) as client:
        reg = client.post(
            "/api/auth/register",
            json={"name": "Live Test", "email": email, "password": password},
        )
        if reg.status_code not in (200, 201, 409):
            pytest.skip(f"Backend unavailable: register -> {reg.status_code}")
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        if login.status_code != 200:
            pytest.skip(f"Backend unavailable: login -> {login.status_code}")
        return login.json()["access_token"]


@pytest.mark.live
def test_live_health():
    with httpx.Client(base_url=BASE, timeout=5.0) as client:
        response = client.get("/health")
        if response.status_code != 200:
            pytest.skip("Backend not running")
        assert response.json()["status"] == "healthy"


@pytest.mark.live
def test_live_authenticated_routes(live_token):
    headers = {"Authorization": f"Bearer {live_token}"}
    paths = [
        "/api/dashboard/stats",
        "/api/leads",
        "/api/scraper/active",
        "/api/scraper/background/status",
        "/api/settings/database",
    ]
    with httpx.Client(base_url=BASE, timeout=10.0) as client:
        for path in paths:
            response = client.get(path, headers=headers)
            assert response.status_code == 200, f"{path} -> {response.status_code}"
