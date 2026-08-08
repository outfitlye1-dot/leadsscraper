"""Email format and deliverability validation."""

from app.utils.contact_utils import is_valid_email


def validate_email(email: str | None) -> bool:
    return bool(email and is_valid_email(email))
