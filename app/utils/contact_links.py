from urllib.parse import quote

from app.models.lead import Lead
from app.schemas.lead import LeadContactLinks
from app.utils.contact_utils import build_whatsapp_link, is_valid_email, is_whatsapp_ready
from app.utils.outreach_tone import sanitize_paid_outreach_message
from app.utils.website_utils import has_real_website


def needs_website_pitch(lead: Lead) -> bool:
    """Offer Website when the business has no real website yet."""
    return not has_real_website(lead.website)


def build_website_offer_message(lead: Lead) -> str:
    company = lead.company_name
    location = ", ".join(p for p in [lead.city, lead.country] if p)
    loc_bit = f" in {location}" if location else ""
    category = lead.category or lead.industry or "business"

    return sanitize_paid_outreach_message(
        f"Hi sir, I saw {company}{loc_bit} — great {category}. "
        f"I help local businesses with a professional website. "
        f"Happy to chat if you're open to it?"
    )


def build_contact_links(lead: Lead) -> LeadContactLinks:
    pitch = needs_website_pitch(lead)
    offer_message = build_website_offer_message(lead) if pitch else ""

    # Plain WhatsApp chat (no pitch) — Offer Website button carries the pitch text
    whatsapp_url = None
    if lead.phone and is_whatsapp_ready(lead.phone, lead.country):
        whatsapp_url = build_whatsapp_link(lead.phone, "")

    email_url = None
    if lead.email and is_valid_email(lead.email):
        subject = quote(f"Hello from {lead.company_name}")
        body = quote(f"Hi, I would like to connect regarding {lead.company_name}.")
        email_url = f"mailto:{lead.email}?subject={subject}&body={body}"

    linkedin = lead.linkedin_url if lead.linkedin_url and lead.linkedin_url.strip() else None
    facebook = lead.facebook_url if lead.facebook_url and lead.facebook_url.strip() else None
    instagram = lead.instagram_url if lead.instagram_url and lead.instagram_url.strip() else None

    offer_whatsapp = None
    offer_email = None
    if pitch:
        if lead.phone and is_whatsapp_ready(lead.phone, lead.country):
            offer_whatsapp = build_whatsapp_link(lead.phone, offer_message)
        if lead.email and is_valid_email(lead.email):
            subject = quote(f"Website offer for {lead.company_name}")
            body = quote(offer_message)
            offer_email = f"mailto:{lead.email}?subject={subject}&body={body}"

    return LeadContactLinks(
        whatsapp_url=whatsapp_url,
        email_url=email_url,
        linkedin_url=linkedin,
        facebook_url=facebook,
        instagram_url=instagram,
        website_url=lead.website if has_real_website(lead.website) else None,
        needs_website_pitch=pitch,
        website_offer_whatsapp_url=offer_whatsapp,
        website_offer_email_url=offer_email,
        offer_message=offer_message if pitch else None,
    )
