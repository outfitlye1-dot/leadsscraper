from unittest.mock import MagicMock

from app.services.lead_service import LeadService
from app.services.scraper_job_store import ScraperJobStore


def test_auto_job_store_cancel_and_stats():
    store = ScraperJobStore()
    job_id = store.create(user_id=1, mode="auto")

    assert store.get_active_auto_job(1) is not None
    store.set_iteration(job_id, 2)
    store.add_auto_stats(job_id, scraped=10, kept=4, deleted=6)

    job = store.get(job_id, 1)
    assert job.iteration == 2
    assert job.auto_kept_total == 4
    assert job.auto_deleted_total == 6

    assert store.request_cancel(job_id, user_id=1) is True
    assert store.is_cancelled(job_id) is True

    store.complete(job_id, {"success": True, "count": 4, "message": "Stopped"})
    assert store.get_active_auto_job(1) is None


def test_cleanup_non_phone_leads_by_ids():
    service = LeadService(MagicMock())
    service.lead_repository = MagicMock()

    with_phone = MagicMock(id=1, is_saved=False, phone="+923001234567")
    without_phone = MagicMock(id=2, is_saved=False, phone=None)
    saved_no_phone = MagicMock(id=3, is_saved=True, phone=None)

    service.lead_repository.get_many_by_ids.return_value = [
        with_phone,
        without_phone,
        saved_no_phone,
    ]
    service.lead_repository.delete_by_ids.return_value = 1

    kept, deleted = service.cleanup_non_phone_leads_by_ids(1, [1, 2, 3])

    assert kept == 1
    assert deleted == 1
    service.lead_repository.save_by_ids.assert_not_called()
    service.lead_repository.delete_by_ids.assert_called_once_with(1, [2], saved=False)
