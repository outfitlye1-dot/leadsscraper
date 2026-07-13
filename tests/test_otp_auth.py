import pytest

from app.services.otp_service import OtpService


@pytest.fixture(autouse=True)
def otp_test_env(monkeypatch):
    monkeypatch.setenv("OTP_DEV_MODE", "true")
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")


@pytest.fixture
def fixed_otp(monkeypatch):
    monkeypatch.setattr(OtpService, "_generate_code", staticmethod(lambda: "123456"))


def test_otp_login_flow(client, fixed_otp):
    client.post(
        "/api/auth/register",
        json={
            "name": "OTP User",
            "email": "otp@example.com",
            "password": "SecurePass123!",
        },
    )

    send = client.post(
        "/api/auth/otp/send",
        json={"email": "otp@example.com", "purpose": "login"},
    )
    assert send.status_code == 200
    assert "expires_in_minutes" in send.json()

    bad = client.post(
        "/api/auth/otp/verify",
        json={"email": "otp@example.com", "code": "000000", "purpose": "login"},
    )
    assert bad.status_code == 400

    verify = client.post(
        "/api/auth/otp/verify",
        json={"email": "otp@example.com", "code": "123456", "purpose": "login"},
    )
    assert verify.status_code == 200
    assert "access_token" in verify.json()


def test_otp_register_flow(client, fixed_otp):
    send = client.post(
        "/api/auth/otp/send",
        json={"email": "newuser@example.com", "purpose": "register"},
    )
    assert send.status_code == 200

    verify = client.post(
        "/api/auth/otp/verify",
        json={
            "email": "newuser@example.com",
            "code": "123456",
            "purpose": "register",
            "name": "New User",
            "password": "SecurePass123!",
        },
    )
    assert verify.status_code == 200
    assert "access_token" in verify.json()

    login = client.post(
        "/api/auth/login",
        json={"email": "newuser@example.com", "password": "SecurePass123!"},
    )
    assert login.status_code == 200

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {verify.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "newuser@example.com"


def test_otp_reset_password_flow(client, fixed_otp):
    client.post(
        "/api/auth/register",
        json={
            "name": "Reset User",
            "email": "reset@example.com",
            "password": "OldPass123!",
        },
    )

    send = client.post(
        "/api/auth/otp/send",
        json={"email": "reset@example.com", "purpose": "reset_password"},
    )
    assert send.status_code == 200

    verify = client.post(
        "/api/auth/otp/verify",
        json={
            "email": "reset@example.com",
            "code": "123456",
            "purpose": "reset_password",
            "password": "NewPass123!",
        },
    )
    assert verify.status_code == 200

    old_login = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": "OldPass123!"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": "NewPass123!"},
    )
    assert new_login.status_code == 200


def test_otp_login_unknown_email(client, fixed_otp):
    response = client.post(
        "/api/auth/otp/send",
        json={"email": "missing@example.com", "purpose": "login"},
    )
    assert response.status_code == 404


def test_otp_register_duplicate_email(client, fixed_otp):
    client.post(
        "/api/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SecurePass123!",
        },
    )
    response = client.post(
        "/api/auth/otp/send",
        json={"email": "jane@example.com", "purpose": "register"},
    )
    assert response.status_code == 409
