def test_lead_database_stats_endpoint(client, auth_headers, db_session):
    from app.models.lead import Lead, LeadStatus

    from app.repositories.user_repository import UserRepository

    user = UserRepository(db_session).get_by_email("test@example.com")
    db_session.add(
        Lead(
            user_id=user.id,
            company_name="Bg Cafe",
            phone="+441234567890",
            source="web_search",
            status=LeadStatus.new,
            intelligence_meta={
                "scrape_context": {
                    "background": True,
                    "keyword": "cafe",
                    "location": "London, UK",
                }
            },
        )
    )
    db_session.commit()

    response = client.get("/api/settings/database", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["database_name"]
    assert data["total_leads"] >= 1
    assert data["background_leads"] >= 1
    assert len(data["recent_background"]) >= 1
