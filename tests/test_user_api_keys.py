import pytest


def test_list_user_keys_empty(client, auth_headers):
    response = client.get("/api/user-keys", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_user_key(client, auth_headers):
    create = client.post(
        "/api/user-keys",
        headers=auth_headers,
        json={
            "provider": "apify",
            "api_key": "apify_api_test_key_12345",
            "label": "My Apify",
        },
    )
    assert create.status_code == 201
    data = create.json()
    assert data["provider"] == "apify"
    assert data["label"] == "My Apify"
    assert "..." in data["masked_key"]
    assert "test_key" not in data["masked_key"]
    assert data["status"] == "active"

    listed = client.get("/api/user-keys?provider=apify", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_bulk_create_user_keys(client, auth_headers):
    response = client.post(
        "/api/user-keys/bulk",
        headers=auth_headers,
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


def test_user_cannot_scrape_without_own_apify_keys(db_session):
    """User with no Apify keys cannot scrape Google Maps."""
    from fastapi import HTTPException

    from app.models.user import User, UserRole
    from app.services.all_in_one_scraper_service import AllInOneScraperService
    from app.schemas.common import ScraperStartRequest

    user = User(
        id=1,
        name="Test",
        email="t@test.com",
        password_hash="x",
        role=UserRole.user,
    )
    db_session.add(user)
    db_session.commit()

    service = AllInOneScraperService(db_session)
    with pytest.raises(HTTPException) as exc:
        service.run(
            user,
            ScraperStartRequest(
                keyword="agency",
                location="Karachi, Pakistan",
                limit=5,
                scrape_source="google_maps",
            ),
        )
    detail = str(exc.value.detail).lower()
    assert "apify" in detail or "api key" in detail


def test_user_keys_are_isolated(client, auth_headers):
    """Keys added by one user are not visible to another user."""
    client.post(
        "/api/user-keys",
        headers=auth_headers,
        json={"provider": "apify", "api_key": "apify_api_user_one_key12"},
    )

    client.post(
        "/api/auth/register",
        json={
            "name": "Other User",
            "email": "other@example.com",
            "password": "OtherPass123!",
        },
    )
    other_login = client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "OtherPass123!"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    other_list = client.get("/api/user-keys", headers=other_headers)
    assert other_list.status_code == 200
    assert other_list.json() == []

    first_list = client.get("/api/user-keys", headers=auth_headers)
    assert len(first_list.json()) == 1


def test_update_and_delete_user_key(client, auth_headers):
    created = client.post(
        "/api/user-keys",
        headers=auth_headers,
        json={"provider": "groq", "api_key": "gsk_update_delete_key12"},
    ).json()

    updated = client.put(
        f"/api/user-keys/{created['id']}",
        headers=auth_headers,
        json={"status": "disabled", "label": "Disabled Key"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "disabled"
    assert updated.json()["label"] == "Disabled Key"

    deleted = client.delete(f"/api/user-keys/{created['id']}", headers=auth_headers)
    assert deleted.status_code == 204

    listed = client.get("/api/user-keys", headers=auth_headers)
    assert listed.json() == []
