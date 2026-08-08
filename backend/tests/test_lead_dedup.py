from app.models.lead import Lead, LeadStatus
from app.utils.lead_dedup import filter_new_leads, lead_match_keys


def test_lead_match_keys_email():
    keys = lead_match_keys({"email": "Test@Example.com", "company_name": "Acme"})
    assert "email:test@example.com" in keys


def test_lead_match_keys_website():
    keys = lead_match_keys({"website": "https://www.example.com", "company_name": "Acme"})
    assert "web:example.com" in keys


def test_filter_new_leads_skips_duplicates():
    existing = [
        Lead(
            user_id=1,
            company_name="Dup Co",
            email="dup@test.com",
            country="US",
            status=LeadStatus.new,
        )
    ]
    scraped = [
        {"company_name": "Dup Co", "email": "dup@test.com"},
        {"company_name": "New Co", "email": "new@test.com"},
    ]
    new_leads, skipped = filter_new_leads(scraped, existing)
    assert len(new_leads) == 1
    assert new_leads[0]["company_name"] == "New Co"
    assert skipped == 1


def test_filter_new_leads_dedupes_within_batch():
    scraped = [
        {"company_name": "Same Co", "email": "same@test.com"},
        {"company_name": "Same Co", "email": "same@test.com"},
    ]
    new_leads, skipped = filter_new_leads(scraped, [])
    assert len(new_leads) == 1
    assert skipped == 1


def test_import_leads_csv(client, auth_headers):
    csv_content = (
        "company_name,email,phone,city,country\n"
        "Import Co,import@test.com,+1234567890,Berlin,Germany\n"
    )
    response = client.post(
        "/api/leads/import",
        headers=auth_headers,
        files={"file": ("leads.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported"] >= 1

    list_resp = client.get("/api/leads?q=Import+Co", headers=auth_headers)
    assert list_resp.json()["total"] >= 1


def test_import_skips_duplicate(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Dup Import", "email": "dupimport@test.com", "status": "new"},
    )
    csv_content = "company_name,email\nDup Import,dupimport@test.com\n"
    response = client.post(
        "/api/leads/import",
        headers=auth_headers,
        files={"file": ("leads.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["skipped_duplicates"] >= 1


def test_list_leads_quality_filter(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={
            "company_name": "Quality Co",
            "email": "q@test.com",
            "phone": "+12345678901",
            "website": "https://quality.com",
            "status": "new",
        },
    )
    response = client.get("/api/leads?has_email=true", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    response2 = client.get("/api/leads?has_website=true", headers=auth_headers)
    assert response2.json()["total"] >= 1


def test_lead_response_includes_quality_fields(client, auth_headers):
    response = client.post(
        "/api/leads",
        headers=auth_headers,
        json={
            "company_name": "Scored Co",
            "email": "scored@test.com",
            "phone": "+12345678901",
            "website": "https://scored.com",
            "status": "new",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "quality_score" in data
    assert "quality_tier" in data
    assert "whatsapp_ready" in data
