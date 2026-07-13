def test_create_lead(client, auth_headers):
    response = client.post(
        "/api/leads",
        headers=auth_headers,
        json={
            "company_name": "Acme Corp",
            "contact_name": "John Smith",
            "email": "john@acme.com",
            "city": "Karachi",
            "country": "Pakistan",
            "industry": "Technology",
            "status": "new",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["company_name"] == "Acme Corp"
    assert data["status"] == "new"


def test_list_leads(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Acme Corp", "status": "new"},
    )
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Beta Inc", "status": "contacted"},
    )
    response = client.get("/api/leads", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_search_leads(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Web Design Agency", "status": "new"},
    )
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Other Company", "status": "new"},
    )
    response = client.get("/api/leads?q=Web+Design", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_update_delete_lead(client, auth_headers):
    create_response = client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Test Corp", "status": "new"},
    )
    lead_id = create_response.json()["id"]

    get_response = client.get(f"/api/leads/{lead_id}", headers=auth_headers)
    assert get_response.status_code == 200

    update_response = client.put(
        f"/api/leads/{lead_id}",
        headers=auth_headers,
        json={"status": "contacted"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "contacted"

    delete_response = client.delete(f"/api/leads/{lead_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    not_found = client.get(f"/api/leads/{lead_id}", headers=auth_headers)
    assert not_found.status_code == 404


def test_export_leads(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Export Corp", "status": "new"},
    )
    response = client.get("/api/leads/export", headers=auth_headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Export Corp" in response.text


def test_bulk_delete_leads_by_ids(client, auth_headers):
    ids = []
    for name in ("Alpha Co", "Beta Co", "Gamma Co"):
        resp = client.post(
            "/api/leads",
            headers=auth_headers,
            json={"company_name": name, "status": "new"},
        )
        ids.append(resp.json()["id"])

    delete_resp = client.post(
        "/api/leads/bulk-delete",
        headers=auth_headers,
        json={"ids": ids[:2]},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] == 2

    list_resp = client.get("/api/leads", headers=auth_headers)
    assert list_resp.json()["total"] == 1


def test_bulk_delete_all_matching(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Keep Me", "status": "new"},
    )
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Remove Me", "status": "contacted"},
    )

    delete_resp = client.post(
        "/api/leads/bulk-delete?status=contacted",
        headers=auth_headers,
        json={"select_all": True},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] == 1

    list_resp = client.get("/api/leads", headers=auth_headers)
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["items"][0]["company_name"] == "Keep Me"


def test_leads_require_auth(client):
    response = client.get("/api/leads")
    assert response.status_code == 401


def test_save_lead_moves_to_saved_list(client, auth_headers):
    create = client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Save Me Co", "status": "new"},
    )
    lead_id = create.json()["id"]

    save = client.post(f"/api/leads/{lead_id}/save", headers=auth_headers)
    assert save.status_code == 200
    assert save.json()["is_saved"] is True

    inbox = client.get("/api/leads", headers=auth_headers)
    assert inbox.json()["total"] == 0

    saved = client.get("/api/leads?saved=true", headers=auth_headers)
    assert saved.json()["total"] == 1
    assert saved.json()["items"][0]["company_name"] == "Save Me Co"


def test_bulk_delete_skips_saved_leads(client, auth_headers):
    keep = client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Keep Saved", "status": "new"},
    ).json()["id"]
    drop = client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Delete Me", "status": "new"},
    ).json()["id"]

    client.post(f"/api/leads/{keep}/save", headers=auth_headers)

    delete_resp = client.post(
        "/api/leads/bulk-delete",
        headers=auth_headers,
        json={"select_all": True},
        params={"saved": False},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] == 1

    saved = client.get("/api/leads?saved=true", headers=auth_headers)
    assert saved.json()["total"] == 1

    inbox = client.get("/api/leads", headers=auth_headers)
    assert inbox.json()["total"] == 0


def test_cleanup_leads_without_contact(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Has Phone", "phone": "+923001234567", "status": "new"},
    )
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Has Email", "email": "hello@company.com", "status": "new"},
    )
    no_contact = client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "No Contact", "status": "new"},
    ).json()["id"]
    saved_no_contact = client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Saved No Contact", "status": "new"},
    ).json()["id"]
    client.post(f"/api/leads/{saved_no_contact}/save", headers=auth_headers)

    response = client.post("/api/leads/cleanup-no-contact", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == 2
    assert data["kept"] == 1

    inbox = client.get("/api/leads", headers=auth_headers)
    assert inbox.json()["total"] == 1
    assert inbox.json()["items"][0]["company_name"] == "Has Phone"

    saved = client.get("/api/leads?saved=true", headers=auth_headers)
    assert saved.json()["total"] == 1
    assert saved.json()["items"][0]["company_name"] == "Saved No Contact"


def test_cleanup_deletes_email_only_leads(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Gmail Only", "email": "user@gmail.com", "status": "new"},
    )
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Has Phone", "phone": "+923001234567", "status": "new"},
    )

    response = client.post("/api/leads/cleanup-no-contact", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["kept"] == 1
    assert response.json()["deleted"] == 1

    inbox = client.get("/api/leads", headers=auth_headers)
    assert inbox.json()["total"] == 1
    assert inbox.json()["items"][0]["company_name"] == "Has Phone"


def test_cleanup_keeps_phone_and_email_lead(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={
            "company_name": "Full Contact",
            "phone": "+923001234567",
            "email": "hello@company.com",
            "status": "new",
        },
    )
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Email Only", "email": "user@gmail.com", "status": "new"},
    )

    response = client.post("/api/leads/cleanup-no-contact", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["kept"] == 1
    assert response.json()["deleted"] == 1

    inbox = client.get("/api/leads", headers=auth_headers)
    assert inbox.json()["total"] == 1
    assert inbox.json()["items"][0]["company_name"] == "Full Contact"


def test_save_leads_with_contact(client, auth_headers):
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Has Phone", "phone": "+923001234567", "status": "new"},
    )
    client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "No Contact", "status": "new"},
    )

    response = client.post("/api/leads/save-with-contact", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["saved"] == 1

    inbox = client.get("/api/leads", headers=auth_headers)
    assert inbox.json()["total"] == 1
    assert inbox.json()["items"][0]["company_name"] == "No Contact"

    saved = client.get("/api/leads?saved=true", headers=auth_headers)
    assert saved.json()["total"] == 1
    assert saved.json()["items"][0]["company_name"] == "Has Phone"
