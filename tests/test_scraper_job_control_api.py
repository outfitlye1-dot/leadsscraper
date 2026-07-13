def test_pause_and_cancel_manual_job(client, auth_headers, db_session):
    from app.models.user import User
    from app.services.scraper_job_store import scraper_job_store

    user = db_session.query(User).filter(User.email == "test@example.com").first()
    job_id = scraper_job_store.create(user.id, mode="single")
    scraper_job_store.update(job_id, status="running")

    pause = client.post(f"/api/scraper/jobs/{job_id}/pause", headers=auth_headers)
    assert pause.status_code == 200
    job = scraper_job_store.get(job_id, user.id)
    assert job.status == "paused"
    assert job.pause_requested

    resume = client.post(f"/api/scraper/jobs/{job_id}/resume", headers=auth_headers)
    assert resume.status_code == 200
    assert scraper_job_store.get(job_id, user.id).status == "running"

    cancel = client.post(f"/api/scraper/jobs/{job_id}/cancel", headers=auth_headers)
    assert cancel.status_code == 200
    assert scraper_job_store.get(job_id, user.id).cancel_requested


def test_job_metrics_endpoint(client, auth_headers, db_session):
    from app.models.user import User
    from app.scraper.metrics import ScrapeMetrics
    from app.services.scraper_job_store import scraper_job_store

    user = db_session.query(User).filter(User.email == "test@example.com").first()
    job_id = scraper_job_store.create(user.id, mode="single")
    metrics = ScrapeMetrics()
    metrics.inc("pages_fetched", 5)
    scraper_job_store.bind_metrics(job_id, metrics)

    response = client.get(f"/api/scraper/jobs/{job_id}/metrics", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["pages_fetched"] == 5


def test_job_history_endpoint(client, auth_headers, db_session):
    from app.models.user import User
    from app.services.scraper_job_store import scraper_job_store

    user = db_session.query(User).filter(User.email == "test@example.com").first()
    job_id = scraper_job_store.create(user.id, mode="single")
    scraper_job_store.complete(job_id, {"success": True, "count": 0, "message": "Done"})

    response = client.get("/api/scraper/jobs/history", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) >= 1
    assert any(j["job_id"] == job_id for j in data["jobs"])
