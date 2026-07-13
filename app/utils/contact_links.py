from urllib.parse import quote

from app.models.lead import Lead
from app.schemas.lead import LeadContactLinks
from app.utils.contact_utils import build_whatsapp_link, is_valid_email, is_whatsapp_ready
from app.utils.outreach_tone import sanitize_paid_outreach_message, CLIENT_PRICING_SNIPPET
from app.utils.website_utils import has_real_website


def needs_website_pitch(lead: Lead) -> bool:
    has_site = has_real_website(lead.website)
    has_instagram = bool(lead.instagram_url and lead.instagram_url.strip())
    return not has_site or not has_instagram


def build_website_offer_message(lead: Lead) -> str:
    name = lead.contact_name or "there"
    company = lead.company_name
    missing_parts = []
    if not has_real_website(lead.website):
        missing_parts.append("professional website")
    if not (lead.instagram_url and lead.instagram_url.strip()):
        missing_parts.append("stronger online presence")

    if len(missing_parts) == 2:
        offer = "a professional website and online presence"
    elif missing_parts:
        offer = missing_parts[0]
    else:
        offer = "a professional website"

    location = ", ".join(p for p in [lead.city, lead.country] if p)
    loc_bit = f" in {location}" if location else ""
    category = lead.category or lead.industry or "business"

    return sanitize_paid_outreach_message(
        f"Hi {name}, I saw {company}{loc_bit} — great {category}. "
        f"I help local businesses with {offer}. "
        f"{CLIENT_PRICING_SNIPPET} "
        f"Happy to share details if you're interested?"
    )


def build_contact_links(lead: Lead) -> LeadContactLinks:
    pitch = needs_website_pitch(lead)
    offer_message = build_website_offer_message(lead) if pitch else ""

    whatsapp_url = None
    if lead.phone and is_whatsapp_ready(lead.phone, lead.country):
        whatsapp_url = build_whatsapp_link(lead.phone, offer_message if pitch else "")

    email_url = None
    if lead.email and is_valid_email(lead.email):
        subject = quote(f"Website for {lead.company_name}")
        body = quote(offer_message if pitch else f"Hi, I would like to connect regarding {lead.company_name}.")
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
