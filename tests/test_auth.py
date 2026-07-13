def test_register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "jane@example.com"
    assert data["name"] == "Jane Doe"
    assert "password" not in data


def test_register_duplicate_email(client):
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "SecurePass123!",
    }
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409


def test_login_success(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SecurePass123!",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "jane@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "WrongPass123!"},
    )
    assert response.status_code == 401


def test_get_me(client, auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_get_me_invalid_token(client):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
