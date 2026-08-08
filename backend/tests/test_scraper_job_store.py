from app.services.scraper_job_store import ScraperJobStore


def test_scraper_job_store_lifecycle():
    store = ScraperJobStore()
    job_id = store.create(user_id=1)

    job = store.get(job_id, user_id=1)
    assert job is not None
    assert job.status == "pending"
    assert job.progress == 0

    store.update(job_id, status="running", progress=25, stage="google_maps", message="Maps...")
    job = store.get(job_id, user_id=1)
    assert job.status == "running"
    assert job.progress == 25
    assert job.stage == "google_maps"

    store.complete(job_id, {"success": True, "count": 5, "message": "Done"})
    job = store.get(job_id, user_id=1)
    assert job.status == "completed"
    assert job.progress == 100
    assert job.result["count"] == 5

    other_job = store.get(job_id, user_id=2)
    assert other_job is None


def test_scraper_job_store_fail():
    store = ScraperJobStore()
    job_id = store.create(user_id=1)
    store.fail(job_id, "Apify error")

    job = store.get(job_id, user_id=1)
    assert job.status == "failed"
    assert job.error == "Apify error"


def test_has_active_manual_job():
    store = ScraperJobStore()
    assert store.has_active_manual_job(42) is False

    job_id = store.create(user_id=42, mode="single")
    assert store.has_active_manual_job(42) is True

    store.complete(job_id, {"success": True, "count": 0, "message": "Done"})
    assert store.has_active_manual_job(42) is False


def test_start_scraper_job_rejects_duplicate_manual():
    import pytest
    from fastapi import HTTPException

    from app.schemas.common import ScraperStartRequest
    from app.services.scraper_job_store import scraper_job_store
    from app.services.scraper_runner import start_scraper_job

    user_id = 424_242
    job_id = scraper_job_store.create(user_id, mode="single")
    scraper_job_store.update(job_id, status="running")
    try:
        req = ScraperStartRequest(keyword="restaurant", location="London, UK", limit=10)
        with pytest.raises(HTTPException) as exc:
            start_scraper_job(user_id, req)
        assert exc.value.status_code == 409
        assert "manual scrape" in str(exc.value.detail).lower()
    finally:
        scraper_job_store.complete(job_id, {"success": True, "count": 0, "message": "cleanup"})


def test_start_auto_scraper_job_rejects_active_manual():
    import pytest
    from fastapi import HTTPException

    from app.schemas.common import ScraperStartRequest
    from app.services.scraper_job_store import scraper_job_store
    from app.services.scraper_runner import start_auto_scraper_job

    user_id = 424_243
    job_id = scraper_job_store.create(user_id, mode="single")
    scraper_job_store.update(job_id, status="running")
    try:
        req = ScraperStartRequest(
            keyword="restaurant",
            location="London, UK",
            limit=10,
            search_query="restaurant London contact phone",
            scrape_source="google_search",
        )
        with pytest.raises(HTTPException) as exc:
            start_auto_scraper_job(user_id, req)
        assert exc.value.status_code == 409
        assert "manual scrape" in str(exc.value.detail).lower()
    finally:
        scraper_job_store.complete(job_id, {"success": True, "count": 0, "message": "cleanup"})
