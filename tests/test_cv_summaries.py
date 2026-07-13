from app.services.groq_service import GroqService


def test_coerce_text_field_from_dict():
    value = {
        "text": "Highly motivated IT professional.",
        "length": 2,
    }
    assert GroqService._coerce_text_field(value) == "Highly motivated IT professional."


def test_coerce_text_field_from_string():
    assert GroqService._coerce_text_field("  hello  ") == "hello"


def test_coerce_text_field_from_list():
    assert GroqService._coerce_text_field(["part one", "part two"]) == "part one part two"
