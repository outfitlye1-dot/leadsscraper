def test_dashboard_excludes_background_leads(client, auth_headers, db_session):
    from app.models.lead import Lead, LeadStatus
    from app.repositories.user_repository import UserRepository

    user = UserRepository(db_session).get_by_email("test@example.com")
    db_session.add(
        Lead(
            user_id=user.id,
            company_name="Manual Lead",
            phone="+441111111111",
            source="web_search",
            status=LeadStatus.new,
        )
    )
    db_session.add(
        Lead(
            user_id=user.id,
            company_name="Background Lead",
            phone="+442222222222",
            source="web_search",
            status=LeadStatus.new,
            intelligence_meta={"scrape_context": {"background": True}},
        )
    )
    db_session.commit()

    response = client.get("/api/dashboard/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_leads"] == 1
    assert data["new_leads"] == 1


def test_is_background_lead_helper():
    from app.models.lead import Lead, LeadStatus
    from app.utils.scrape_context import is_background_lead

    manual = Lead(
        user_id=1,
        company_name="Manual",
        source="web_search",
        status=LeadStatus.new,
    )
    background = Lead(
        user_id=1,
        company_name="Bg",
        source="web_search",
        status=LeadStatus.new,
        intelligence_meta={"scrape_context": {"background": True}},
    )
    assert is_background_lead(manual) is False
    assert is_background_lead(background) is True
