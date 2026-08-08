"""Tenant isolation for WhatsApp inbound phone matching."""

from app.services.whatsapp_chat_service import WhatsAppChatService


def test_phone_digits_match_suffix():
    svc = WhatsAppChatService.__new__(WhatsAppChatService)
    assert svc._phone_digits_match("+39 380 634 2394", "393806342394")
    assert svc._phone_digits_match("923001234567", "3001234567")
    assert not svc._phone_digits_match("123", "456")
    assert not svc._phone_digits_match("", "393806342394")
