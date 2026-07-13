from app.services.groq_service import GroqService


def test_extract_system_prompt_plain_text():
    svc = GroqService()
    text = "You are a professional outreach assistant. " + ("Help the user. " * 40)
    assert svc._extract_system_prompt(text).startswith("You are a professional")
    assert len(svc._extract_system_prompt(text)) >= 200


def test_extract_system_prompt_json():
    svc = GroqService()
    text = '{"system_prompt": "You are a sales expert. "}'
    extracted = svc._extract_system_prompt(text)
    assert extracted.startswith("You are a sales expert")


def test_extract_system_prompt_markdown_json():
    svc = GroqService()
    text = '```json\n{"system_prompt": "You are an AI brain for outreach."}\n```'
    extracted = svc._extract_system_prompt(text)
    assert "AI brain" in extracted


def test_extract_system_prompt_rejects_short():
    svc = GroqService()
    assert svc._extract_system_prompt("ok") == ""
