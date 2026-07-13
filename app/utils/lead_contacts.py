from app.utils.contact_utils import (
    format_contact_phone,
    is_valid_email,
    is_whatsapp_ready,
    pick_best_email,
    pick_best_phone,
    score_email,
    score_phone,
    _effective_country_for_phone,
)
from app.utils.contact_verifier import verify_email_deliverability


def sanitize_lead_contacts(lead_data: dict, search_location: str | None = None) -> dict:
    """Normalize email + phone; keep real contacts, drop obvious junk only."""
    cleaned = dict(lead_data)
    country = cleaned.get("country")
    website = cleaned.get("website")
    location_hint = search_location or country

    email = cleaned.get("email")
    if email:
        email = email.strip().lower()
        if not is_valid_email(email):
            email = None
        elif not verify_email_deliverability(email, website):
            email = None
        cleaned["email"] = email
    else:
        cleaned["email"] = None

    phone = cleaned.get("phone")
    phone_country = _effective_country_for_phone(phone, country) or country
    formatted = format_contact_phone(phone, phone_country)
    from app.utils import phone_lib

    if formatted:
        if location_hint and not phone_lib.phone_matches_search_region(formatted, location_hint):
            cleaned["phone"] = None
        else:
            cleaned["phone"] = formatted
    else:
        cleaned["phone"] = None

    return cleaned


def merge_contact_fields(
    lead_data: dict,
    page_text: str,
    country: str | None,
) -> None:
    website = lead_data.get("website")
    from app.utils.contact_utils import extract_emails_from_text, extract_phones_from_text

    phone_country = _effective_country_for_phone(lead_data.get("phone"), country) or country

    emails = extract_emails_from_text(page_text, website)
    if emails:
        best = pick_best_email(emails, website)
        if best and (
            not lead_data.get("email")
            or score_email(best, website) > score_email(lead_data.get("email") or "", website)
        ):
            lead_data["email"] = best

    phones = extract_phones_from_text(page_text, phone_country)
    if phones:
        best_phone = pick_best_phone(phones, phone_country)
        current = lead_data.get("phone")
        if best_phone and (
            not current
            or score_phone(best_phone, phone_country) > score_phone(current, phone_country)
        ):
            lead_data["phone"] = best_phone
