import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.database import get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_scraper_job_store():
    from app.services.scraper_job_store import scraper_job_store

    with scraper_job_store._lock:
        scraper_job_store._jobs.clear()
        scraper_job_store._active_auto.clear()
        scraper_job_store._metrics.clear()
    yield
    with scraper_job_store._lock:
        scraper_job_store._jobs.clear()
        scraper_job_store._active_auto.clear()
        scraper_job_store._metrics.clear()


@pytest.fixture(autouse=True)
def configure_test_env(monkeypatch):
    monkeypatch.setenv("SCRAPER_VERIFY_EMAIL_MX", "false")


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "TestPass123!",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "TestPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def groq_auth_headers(client, auth_headers):
    client.post(
        "/api/user-keys",
        headers=auth_headers,
        json={"provider": "groq", "api_key": "gsk_test_user_groq_key12"},
    )
    return auth_headers
