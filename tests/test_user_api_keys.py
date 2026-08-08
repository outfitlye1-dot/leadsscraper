import pytest


@pytest.fixture
def admin_headers(client, db_session):
    from app.models.user import User, UserRole

    client.post(
        "/api/auth/register",
        json={
            "name": "Admin User",
            "email": "admin@example.com",
            "password": "AdminPass123!",
        },
    )
    user = db_session.query(User).filter(User.email == "admin@example.com").first()
    assert user is not None
    user.role = UserRole.admin
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_regular_user_cannot_manage_keys(client, auth_headers):
    response = client.get("/api/user-keys", headers=auth_headers)
    assert response.status_code == 403

    create = client.post(
        "/api/user-keys",
        headers=auth_headers,
        json={
            "provider": "apify",
            "api_key": "apify_api_test_key_12345",
            "label": "My Apify",
        },
    )
    assert create.status_code == 403


def test_list_platform_keys_empty(client, admin_headers):
    response = client.get("/api/user-keys", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_admin_create_and_list_platform_key(client, admin_headers):
    create = client.post(
        "/api/user-keys",
        headers=admin_headers,
        json={
            "provider": "apify",
            "api_key": "apify_api_test_key_12345",
            "label": "Platform Apify",
        },
    )
    assert create.status_code == 201
    data = create.json()
    assert data["provider"] == "apify"
    assert data["label"] == "Platform Apify"
    assert "..." in data["masked_key"]
    assert "test_key" not in data["masked_key"]
    assert data["status"] == "active"

    listed = client.get("/api/user-keys?provider=apify", headers=admin_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_admin_bulk_create_platform_keys(client, admin_headers):
    response = client.post(
        "/api/user-keys/bulk",
        headers=admin_headers,
        json={
            "provider": "groq",
            "api_keys": [
                "gsk_test_key_one_abcdefgh",
                "gsk_test_key_two_abcdefgh",
                "short",
            ],
            "label_prefix": "Groq",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["created"] == 2
    assert len(data["keys"]) == 2
    assert data["keys"][0]["priority"] == 0
    assert data["keys"][1]["priority"] == 1


def test_maps_scrape_works_without_apify_keys(db_session):
    """Google Maps uses Playwright — no Apify key required."""
    from unittest.mock import MagicMock, patch

    from app.models.user import User, UserRole
    from app.services.all_in_one_scraper_service import AllInOneScraperService
    from app.schemas.common import ScraperStartRequest
    from app.models.lead import LeadStatus

    user = User(
        id=1,
        name="Test",
        email="t@test.com",
        password_hash="x",
        role=UserRole.user,
    )
    db_session.add(user)
    db_session.commit()

    mock_leads = [
        {
            "company_name": "Local Shop",
            "phone": "+923001234567",
            "email": None,
            "website": None,
            "country": "Pakistan",
            "source": "playwright_maps",
            "status": LeadStatus.new,
        }
    ]

    with (
        patch("app.services.all_in_one_scraper_service.get_settings") as mock_settings,
        patch("app.services.all_in_one_scraper_service.EnrichmentService") as mock_enrich_class,
        patch("app.services.all_in_one_scraper_service.ApifyService") as mock_apify_class,
    ):
        mock_settings.return_value.SCRAPER_PLAYWRIGHT_MAPS_MAX_SECONDS = 90.0
        mock_apify = MagicMock()
        mock_apify._normalize_location.side_effect = lambda x: x
        mock_apify.scrape_maps_playwright_local.return_value = mock_leads
        mock_apify.web_search_service.search_leads.return_value = []
        mock_apify.count_by_source.return_value = (1, 0, 0)
        mock_apify_class.return_value = mock_apify
        mock_enrich = MagicMock()
        mock_enrich.enrich_leads_batch.side_effect = lambda leads, on_progress=None: leads
        mock_enrich_class.return_value = mock_enrich

        service = AllInOneScraperService(db_session)
        result = service.run(
            user,
            ScraperStartRequest(
                keyword="agency",
                location="Karachi, Pakistan",
                limit=5,
                scrape_source="google_maps",
                enrich_contacts=False,
                auto_generate_whatsapp=False,
            ),
        )

    assert result.success is True
    assert result.count == 1
    mock_apify.scrape_maps_playwright_local.assert_called()


def test_regular_user_uses_admin_platform_keys(client, auth_headers, admin_headers, db_session):
    """Admin adds keys; regular users get them via rotation service."""
    from app.models.user_api_key import ApiProvider
    from app.services.api_key_rotation_service import ApiKeyRotationService
    from app.models.user import User

    client.post(
        "/api/user-keys",
        headers=admin_headers,
        json={"provider": "groq", "api_key": "gsk_platform_shared_key12"},
    )

    regular = db_session.query(User).filter(User.email == "test@example.com").first()
    assert regular is not None
    tokens = ApiKeyRotationService(db_session).get_user_tokens(regular.id, ApiProvider.groq)
    assert tokens == ["gsk_platform_shared_key12"]


def test_update_and_delete_platform_key(client, admin_headers):
    created = client.post(
        "/api/user-keys",
        headers=admin_headers,
        json={"provider": "groq", "api_key": "gsk_update_delete_key12"},
    ).json()

    updated = client.put(
        f"/api/user-keys/{created['id']}",
        headers=admin_headers,
        json={"status": "disabled", "label": "Disabled Key"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "disabled"
    assert updated.json()["label"] == "Disabled Key"

    deleted = client.delete(f"/api/user-keys/{created['id']}", headers=admin_headers)
    assert deleted.status_code == 204

    listed = client.get("/api/user-keys", headers=admin_headers)
    assert listed.json() == []
