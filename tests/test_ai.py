from io import BytesIO
from unittest.mock import MagicMock, patch

import docx


@patch("app.services.message_service.GroqService")
@patch("app.services.cv_service.GroqService")
def test_generate_whatsapp_message(
    mock_cv_groq_class, mock_msg_groq_class, client, groq_auth_headers
):
    mock_cv_groq = MagicMock()
    mock_cv_groq.extract_cv_profile.return_value = {
        "name": "John Doe",
        "skills": ["Python"],
        "experience": [],
        "education": [],
        "projects": [],
        "services": ["Web Development"],
        "tools": [],
        "technologies": [],
    }
    mock_cv_groq.generate_summaries.return_value = {
        "professional_summary": "Engineer",
        "skills_summary": "Python",
        "services_summary": "Web dev",
        "experience_summary": "5 years",
    }
    mock_cv_groq_class.return_value = mock_cv_groq

    document = docx.Document()
    document.add_paragraph("John Doe Software Engineer Python FastAPI")
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)

    client.post(
        "/api/cv/upload",
        headers=groq_auth_headers,
        files={
            "file": (
                "resume.docx",
                buffer.read(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    lead_response = client.post(
        "/api/leads",
        headers=groq_auth_headers,
        json={"company_name": "Acme Corp", "contact_name": "Jane", "status": "new"},
    )
    lead_id = lead_response.json()["id"]

    mock_msg_groq = MagicMock()
    mock_msg_groq.generate_message.return_value = (
        "Hi Jane, I noticed Acme Corp's work. I offer web development services.",
        "Hi Jane, I noticed Acme Corp's work. I offer web development services.",
    )
    mock_msg_groq_class.return_value = mock_msg_groq

    response = client.post(
        "/api/ai/generate",
        headers=groq_auth_headers,
        json={"lead_id": lead_id, "message_type": "whatsapp"},
    )
    assert response.status_code == 200
    assert "message" in response.json()

    messages_response = client.get("/api/messages", headers=groq_auth_headers)
    assert messages_response.status_code == 200
    assert messages_response.json()["total"] == 1


def test_generate_message_requires_cv(client, auth_headers):
    lead_response = client.post(
        "/api/leads",
        headers=auth_headers,
        json={"company_name": "Acme Corp", "status": "new"},
    )
    lead_id = lead_response.json()["id"]

    response = client.post(
        "/api/ai/generate",
        headers=auth_headers,
        json={"lead_id": lead_id, "message_type": "whatsapp"},
    )
    assert response.status_code == 400


@patch("app.routes.ai.GroqService")
def test_optimize_search_query(mock_groq_class, client, auth_headers):
    mock_groq = mock_groq_class.return_value
    mock_groq.optimize_search_query.return_value = {
        "optimized_query": "web design agency Karachi Pakistan contact email",
        "suggestions": [
            "web design agency Karachi Pakistan contact email",
            "web design Lahore Pakistan phone",
        ],
        "tips": "Added location and contact keywords",
        "was_corrected": True,
    }

    response = client.post(
        "/api/ai/optimize-search-query",
        headers=auth_headers,
        json={"query": "web design karachi"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "optimized_query" in data
    assert len(data["suggestions"]) >= 1
    assert data["was_corrected"] is True


@patch("app.services.scrape_suggest_service.GroqService")
def test_suggest_scrape_from_brain(mock_suggest_groq_class, client, groq_auth_headers, db_session):
    from app.models.brain import Brain
    from app.repositories.user_repository import UserRepository

    user = UserRepository(db_session).get_by_email("test@example.com")
    db_session.add(
        Brain(
            user_id=user.id,
            name="Ali Khan",
            services=["Web Design"],
            skills=["React"],
            professional_summary="Web designer for local businesses",
            custom_notes="Target Lahore, Pakistan",
        )
    )
    db_session.commit()

    mock_suggest_groq = mock_suggest_groq_class.return_value
    mock_suggest_groq._has_groq_access.return_value = True
    mock_suggest_groq.suggest_scrape_from_profile.return_value = {
        "recommended_keyword": "restaurant",
        "recommended_location": "",
        "recommended_search_query": "restaurant contact email phone",
        "keyword_suggestions": ["restaurant", "cafe"],
        "location_suggestions": [],
        "search_queries": ["restaurant contact email phone"],
        "strategy_tips": "Target restaurants needing websites",
        "profile_name": "Ali Khan",
        "has_profile": True,
    }

    response = client.post(
        "/api/ai/suggest-scrape",
        headers=groq_auth_headers,
        json={"scrape_source": "all"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_keyword"] == "restaurant"
    assert data["recommended_location"] == ""
    assert data["location_suggestions"] == []
    assert data["has_profile"] is True
    assert len(data["search_queries"]) >= 1


def test_suggest_scrape_fallback_without_brain_or_groq(client, auth_headers):
    response = client.post(
        "/api/ai/suggest-scrape",
        headers=auth_headers,
        json={"scrape_source": "google_search"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_profile"] is False
    assert data["recommended_keyword"]
    assert len(data["search_queries"]) >= 1


def test_cv_scrape_suggest_prompt_formats_without_keyerror():
    from app.utils.prompts import CV_SCRAPE_SUGGEST_PROMPT
    from app.utils.prompt_format import safe_prompt_format

    formatted = safe_prompt_format(
        CV_SCRAPE_SUGGEST_PROMPT,
        profile='{"services": ["web agency"]}',
        scrape_source="google_maps",
    )
    assert "local" in formatted.lower()
    assert "google_maps" in formatted


def test_safe_prompt_format_handles_stray_braces_in_profile():
    from app.utils.prompt_format import safe_prompt_format

    template = "Profile:\n{profile}\nMode: {scrape_source}"
    result = safe_prompt_format(
        template,
        profile='{"note": "{service} and {unknown}"}',
        scrape_source="all",
    )
    assert '"{service} and {unknown}"' in result
    assert "Mode: all" in result
