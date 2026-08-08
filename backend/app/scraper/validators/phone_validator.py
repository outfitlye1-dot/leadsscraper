"""Phone number validation (mobile / WhatsApp-ready)."""

from app.utils.contact_utils import is_whatsapp_ready, normalize_whatsapp_phone


def validate_phone(phone: str | None, country: str | None = None) -> bool:
    return bool(phone and normalize_whatsapp_phone(phone, country))


def validate_whatsapp_phone(phone: str | None, country: str | None = None) -> bool:
    return bool(phone and is_whatsapp_ready(phone, country))
