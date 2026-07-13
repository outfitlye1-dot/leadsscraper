def test_list_leads_hides_background(client, auth_headers, db_session):
    from app.models.lead import Lead, LeadStatus
    from app.repositories.user_repository import UserRepository

    user = UserRepository(db_session).get_by_email("test@example.com")
    db_session.add(
        Lead(
            user_id=user.id,
            company_name="Visible Lead",
            source="manual",
            status=LeadStatus.new,
        )
    )
    db_session.add(
        Lead(
            user_id=user.id,
            company_name="Hidden Background Lead",
            source="web_search",
            status=LeadStatus.new,
            intelligence_meta={"scrape_context": {"background": True}},
        )
    )
    db_session.commit()

    response = client.get("/api/leads", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["company_name"] == "Visible Lead"


def test_cache_promotes_background_leads_to_inbox(client, auth_headers, db_session):
    from app.models.lead import Lead, LeadStatus
    from app.repositories.user_repository import UserRepository
    from app.schemas.common import ScraperStartRequest
    from app.services.scrape_cache_service import ScrapeCacheService
    from app.utils.scrape_sources import ScrapeSourceMode
    from app.utils.website_utils import WebsiteFilter

    user = UserRepository(db_session).get_by_email("test@example.com")
    db_session.add(
        Lead(
            user_id=user.id,
            company_name="Cached Cafe",
            phone="+441234567890",
            source="web_search",
            status=LeadStatus.new,
            city="London",
            country="United Kingdom",
            intelligence_meta={
                "scrape_context": {
                    "background": True,
                    "keyword": "restaurant",
                    "location": "London, United Kingdom",
                    "scrape_source": "google_search",
                    "website_filter": "all",
                }
            },
        )
    )
    db_session.commit()

    req = ScraperStartRequest(
        keyword="restaurant",
        location="London, United Kingdom",
        scrape_source=ScrapeSourceMode.google_search,
        website_filter=WebsiteFilter.all,
        limit=10,
    )
    result = ScrapeCacheService(db_session).try_fulfill_from_cache(user.id, req)
    assert result is not None
    assert result.count == 1

    response = client.get("/api/leads", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["company_name"] == "Cached Cafe"
