from app.models.lead import Lead, LeadStatus
from app.schemas.common import ScraperStartRequest
from app.utils.scrape_context import (
    lead_matches_scrape_request,
    scrape_request_signature,
    tag_leads_with_scrape_context,
)
from app.utils.scrape_sources import ScrapeSourceMode
from app.utils.website_utils import WebsiteFilter


def test_scrape_signature_stable():
    req = ScraperStartRequest(
        keyword="restaurant",
        location="London, UK",
        search_query="restaurant London contact phone",
        scrape_source=ScrapeSourceMode.google_search,
        website_filter=WebsiteFilter.without_website,
        limit=10,
    )
    assert scrape_request_signature(req) == scrape_request_signature(req)


def test_tagged_lead_matches_request():
    req = ScraperStartRequest(
        keyword="salon",
        location="Berlin, Germany",
        scrape_source=ScrapeSourceMode.google_search,
        website_filter=WebsiteFilter.without_website,
        limit=10,
    )
    tagged = tag_leads_with_scrape_context(
        [{"company_name": "Bella Salon", "source": "web_search", "status": LeadStatus.new}],
        req,
        background=True,
    )[0]
    lead = Lead(
        id=1,
        user_id=1,
        company_name=tagged["company_name"],
        intelligence_meta=tagged["intelligence_meta"],
        source="web_search",
        status=LeadStatus.new,
    )
    assert lead_matches_scrape_request(lead, req)


def test_cache_service_threshold():
    from app.services.scrape_cache_service import ScrapeCacheService

    class FakeLead:
        def __init__(self, i: int):
            self.id = i
            self.website = None

    class FakeRepo:
        def find_background_for_scrape_request(self, user_id, data, limit):
            return [FakeLead(i) for i in range(5)]

        def promote_background_leads(self, user_id, lead_ids):
            return len(lead_ids)

    svc = ScrapeCacheService(db=None)  # type: ignore[arg-type]
    svc.lead_repository = FakeRepo()
    req = ScraperStartRequest(
        keyword="gym",
        location="Paris, France",
        scrape_source=ScrapeSourceMode.google_search,
        website_filter=WebsiteFilter.without_website,
        limit=10,
    )
    result = svc.try_fulfill_from_cache(1, req)
    assert result is not None
    assert result.count == 5


def test_ensure_restarts_dead_worker():
    from unittest.mock import patch

    from app.services.background_scrape_runner import ensure_background_scraper
    from app.services.background_scrape_store import background_scrape_store

    user_id = 88_002
    background_scrape_store.touch_heartbeat(user_id)

    with patch("app.services.background_scrape_runner.threading.Thread") as thread_cls:
        fake_thread = thread_cls.return_value
        ensure_background_scraper(user_id)
        thread_cls.assert_called_once()
        fake_thread.start.assert_called_once()


def test_start_worker_if_dead_is_atomic():
    from unittest.mock import MagicMock

    from app.services.background_scrape_store import BackgroundScrapeStore

    store = BackgroundScrapeStore()
    user_id = 77_001
    started = []

    def factory(stop_event):
        thread = MagicMock()
        thread.is_alive.return_value = True
        started.append(thread)
        return thread

    assert store.start_worker_if_dead(user_id, factory) is True
    assert store.start_worker_if_dead(user_id, factory) is False
    assert len(started) == 1


def test_stop_worker_keeps_thread_until_exit():
    from unittest.mock import MagicMock

    from app.services.background_scrape_store import BackgroundScrapeStore

    store = BackgroundScrapeStore()
    user_id = 77_002
    alive = MagicMock()
    alive.is_alive.return_value = True

    store.set_thread(user_id, alive)
    store.stop_worker(user_id)

    assert store.is_worker_alive(user_id) is True
    assert store.start_worker_if_dead(user_id, MagicMock()) is False

    alive.is_alive.return_value = False
    store.clear_thread(user_id)
    assert store.is_worker_alive(user_id) is False


def test_background_store_logs_and_progress():
    from app.services.background_scrape_store import background_scrape_store

    user_id = 99_001
    background_scrape_store.append_log(user_id, "Round 1 started", level="info", stage="init")
    background_scrape_store.update_progress(user_id, 42, "crawl", "Fetching pages...")
    status = background_scrape_store.get_status(user_id)

    assert len(status["logs"]) == 1
    assert status["logs"][0]["text"] == "Round 1 started"
    assert status["progress"] == 42
    assert status["stage"] == "crawl"
    assert status["message"] == "Fetching pages..."
