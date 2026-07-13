def test_active_scraper_job_returns_running_manual(client, auth_headers, db_session):
    from app.models.user import User
    from app.services.scraper_job_store import scraper_job_store

    response = client.get("/api/scraper/active", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() is None

    user = db_session.query(User).filter(User.email == "test@example.com").first()
    job_id = scraper_job_store.create(user.id, mode="single")
    scraper_job_store.update(job_id, status="running", progress=10, stage="init", message="Working")

    response = client.get("/api/scraper/active", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["job_id"] == job_id
    assert data["status"] == "running"

    scraper_job_store.complete(job_id, {"success": True, "count": 0, "message": "Done"})


def test_duplicate_manual_scrape_returns_409(client, auth_headers, db_session):
    from app.models.user import User
    from app.schemas.common import ScraperStartRequest
    from app.services.scraper_job_store import scraper_job_store
    from app.services.scraper_runner import start_scraper_job

    user = db_session.query(User).filter(User.email == "test@example.com").first()
    job_id = scraper_job_store.create(user.id, mode="single")
    scraper_job_store.update(job_id, status="running")

    response = client.post(
        "/api/scraper/start",
        headers=auth_headers,
        json={
            "keyword": "salon",
            "location": "Paris, France",
            "search_query": "salon Paris contact phone",
            "scrape_source": "google_search",
            "limit": 10,
        },
    )
    assert response.status_code == 409

    scraper_job_store.complete(job_id, {"success": True, "count": 0, "message": "Done"})
