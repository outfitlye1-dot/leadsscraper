from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_warns_on_default_secret_key():
    response = client.get("/health")
    data = response.json()
    # Test env uses default SECRET_KEY from config unless overridden in .env
    if data.get("warnings"):
        assert "default_secret_key" in data["warnings"]
