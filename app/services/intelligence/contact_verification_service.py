"""Contact verification — phone, email, WhatsApp readiness."""

from __future__ import annotations

from app.utils.contact_utils import (
    format_contact_phone,
    is_junk_email,
    is_valid_email,
    is_whatsapp_ready,
)
from app.utils.contact_verifier import verify_email_deliverability
from app.utils.phone_lib import phone_matches_search_region


def verify_lead_contacts(lead: dict, search_location: str | None = None) -> dict:
    location = search_location or lead.get("country") or ""
    phone = lead.get("phone")
    email = lead.get("email")
    website = lead.get("website")

    phone_verified = False
    if phone:
        formatted = format_contact_phone(phone, lead.get("country"))
        digits_ok = formatted and len("".join(c for c in formatted if c.isdigit())) >= 10
        region_ok = not location or phone_matches_search_region(phone, location)
        phone_verified = bool(digits_ok and region_ok)

    email_verified = False
    if email and is_valid_email(email) and not is_junk_email(email):
        email_verified = verify_email_deliverability(email, website)

    lead["phone_verified"] = phone_verified
    lead["email_verified"] = email_verified
    lead["whatsapp_ready"] = bool(
        phone and is_whatsapp_ready(phone, lead.get("country")) and phone_verified
    )

    meta = dict(lead.get("intelligence_meta") or {})
    meta["contact_verification"] = {
        "phone_verified": phone_verified,
        "email_verified": email_verified,
        "whatsapp_ready": lead.get("whatsapp_ready"),
    }
    lead["intelligence_meta"] = meta
    return lead
