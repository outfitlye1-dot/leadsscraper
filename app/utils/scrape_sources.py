import re
from enum import Enum
from urllib.parse import urlparse

from app.models.lead import LeadStatus
from app.utils.contact_utils import (
    extract_emails_from_text,
    extract_phones_from_snippet,
    format_contact_phone,
    infer_country_from_location,
    is_valid_email,
    is_whatsapp_ready,
    pick_best_email,
    pick_best_phone,
)
from app.utils.lead_contacts import sanitize_lead_contacts
from app.utils.website_utils import (
    has_real_website,
    is_google_maps_url,
    is_social_only_url,
    normalize_website_field,
)


class ScrapeSourceMode(str, Enum):
    all = "all"
    google_maps = "google_maps"
    google_search = "google_search"
    meta_ads = "meta_ads"


def build_internet_search_query(keyword: str, location: str) -> str:
    """Maps-style free internet query from keyword + location."""
    kw = (keyword or "").strip()
    loc = (location or "").strip()
    if kw and loc:
        return f"{kw} {loc} contact email phone whatsapp"
    if kw:
        return f"{kw} contact email phone whatsapp"
    if loc:
        return f"local business {loc} contact email phone whatsapp"
    return ""


SKIP_SEARCH_DOMAINS = (
    "google.com",
    "google.com.pk",
    "youtube.com",
    "wikipedia.org",
    "yelp.com",
    "tripadvisor.com",
    "pinterest.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "quora.com",
    "medium.com",
    "amazon.com",
    "ebay.com",
    "booking.com",
    "hotels.com",
    "trustpilot.com",
    "glassdoor.com",
    "indeed.com",
    "crunchbase.com",
    "stackoverflow.com",
    "github.com",
    "bing.com",
    "brownbook.net",
    "kompass.com",
    "tradeindia.com",
    "alibaba.com",
    "indiamart.com",
    "bark.com",
    "thumbtack.com",
    "angi.com",
    "houzz.com",
    "manta.com",
    "showmelocal.com",
    "tupalo.com",
    "locanto.com",
    "gumtree.com",
    "olx.com",
    "zillow.com",
    "zomato.com",
    "foodpanda.com",
    "duckduckgo.com",
)

DIRECTORY_AGGREGATOR_HINTS = (
    "clutch.co",
    "designrush.com",
    "goodfirms.co",
    "sortlist.com",
    "upcity.com",
    "manifest.com",
    "freeola.com",
    "justdial",
    "yellowpages",
    "yell.com",
    "hotfrog",
    "cylex",
    "foursquare",
    "findglocal",
    "businesslist",
    "business-directory",
    "businessdirectory",
    "pakbiz",
    "listings",
    "/directory/",
    "/listings/",
    "/companies/",
    "/category/",
    "/top-",
    "/best-",
    "/listicles/",
    "/agency/",
    "/webdesigners/",
    "/blog/",
    "/news/",
    "/article/",
    "/guide/",
)

LISTICLE_URL_PATH_HINTS = (
    "/listicles/",
    "/agency/",
    "/companies/",
    "/webdesigners/",
    "/top-",
    "/best-",
    "/directory/",
    "/listings/",
)

LISTICLE_TITLE_PATTERN = re.compile(
    r"(?:"
    r"\btop\s+\d+\b|\bbest\s+\d+\b|\b\d+\s+best\b|\b\d+\s+top\b|"
    r"\btop\s+\w+(?:\s+\w+){0,4}\s+companies?\s+(?:in|near)\b|"
    r"\bbest\s+\w+(?:\s+\w+){0,4}\s+companies?\s+(?:in|near|for)\b|"
    r"\bcompanies?\s+in\s+[A-Za-z]|\bbest\s+\w+\s+(?:in|for|near)\b|"
    r"\blist\s+of\b|\bguide\s+to\b|"
    r"\bhow\s+to\s+(?:choose|find|pick)\b|\bcompare\s+\d+\b|"
    r"\branking\b|\bdirectory\b|\bnear\s+me\b|\bfind\s+a\b|"
    r"\breviews?\s*:|\bvs\.?\b|\bcomparison\b|\broundup\b|"
    r"\bpresents\b"
    r")",
    re.IGNORECASE,
)

EUROPE_LOCATION_MARKERS = (
    "united kingdom",
    "uk",
    "gb",
    "england",
    "london",
    "berlin",
    "germany",
    "france",
    "paris",
    "amsterdam",
    "netherlands",
    "madrid",
    "spain",
    "dublin",
    "ireland",
    "europe",
)

FOREIGN_TITLE_MARKERS = (
    "lahore",
    "karachi",
    "islamabad",
    "pakistan",
    "india",
    "mumbai",
    "delhi",
    "bangalore",
    "dubai",
    "uae",
)

GENERIC_TITLE_SEGMENTS = frozenset(
    {
        "home",
        "homepage",
        "welcome",
        "official site",
        "official website",
        "index",
        "main",
        "about us",
        "contact us",
        "contact",
        "about",
        "services",
        "products",
        "blog",
        "news",
    }
)

TITLE_SEPARATOR_PATTERN = re.compile(r"\s*[\|–\-:]\s*")


def _host(url: str) -> str:
    try:
        host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def is_listicle_url(url: str | None) -> bool:
    if not url:
        return False
    path = urlparse(url if "://" in url else f"https://{url}").path.lower()
    return any(hint in path for hint in LISTICLE_URL_PATH_HINTS)


def is_directory_or_aggregator_url(url: str | None) -> bool:
    if not url:
        return False
    host = _host(url)
    path = urlparse(url if "://" in url else f"https://{url}").path.lower()
    combined = f"{host}{path}"
    if is_listicle_url(url):
        return True
    return any(hint in combined for hint in DIRECTORY_AGGREGATOR_HINTS)


def title_conflicts_with_location(title: str | None, location: str | None) -> bool:
    if not title or not location:
        return False
    loc_lower = location.lower()
    if not any(marker in loc_lower for marker in EUROPE_LOCATION_MARKERS):
        return False
    title_lower = title.lower()
    return any(marker in title_lower for marker in FOREIGN_TITLE_MARKERS)


def is_listicle_or_bad_title(title: str | None) -> bool:
    if not title:
        return True
    cleaned = title.strip()
    if len(cleaned) < 2 or len(cleaned) > 120:
        return True
    if LISTICLE_TITLE_PATTERN.search(cleaned):
        return True
    lower = cleaned.lower()
    if lower in GENERIC_TITLE_WORDS:
        return True
    return False


def is_hostname_company_name(company_name: str, website: str | None) -> bool:
    if not company_name or not website:
        return False
    host = _host(website).split(".")[0].replace("-", "").replace("_", "")
    name = re.sub(r"[^a-z0-9]", "", company_name.lower())
    return bool(host and name and host == name)


def should_skip_search_url(url: str | None) -> bool:
    if not url:
        return True
    if is_google_maps_url(url):
        return True
    if is_social_only_url(url):
        return True
    if is_listicle_url(url):
        return True
    if is_directory_or_aggregator_url(url):
        return True
    host = _host(url)
    return any(skip in host for skip in SKIP_SEARCH_DOMAINS)


GENERIC_TITLE_WORDS = frozenset(
    {
        "home",
        "homepage",
        "welcome",
        "index",
        "untitled",
        "404",
        "error",
        "page not found",
        "coming soon",
        "under construction",
    }
)


def _is_bare_domain(name: str) -> bool:
    return bool(re.match(r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$", name.strip().lower()))


def derive_industry_hint(keyword: str, search_query: str | None = None) -> str | None:
    """Best-effort category from the user's scrape query."""
    keyword = keyword.strip()
    search_query = (search_query or "").strip()

    if search_query and (not keyword or len(search_query) > len(keyword) + 10):
        base = search_query
    else:
        base = keyword or search_query

    if not base:
        return None
    cleaned = re.sub(
        r"\b(contact|email|phone|whatsapp|business|website|company|near me)\b",
        " ",
        base,
        flags=re.I,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    if len(cleaned) < 3:
        return None
    return cleaned[:255].title()


def derive_maps_search_params(
    keyword: str,
    location: str,
    search_query: str | None = None,
) -> tuple[str, str]:
    """Build Google Maps keyword + location when internet scrape returns no leads."""
    from app.utils.scrape_defaults import normalize_location_alias, resolve_scrape_location

    maps_keyword = derive_industry_hint(keyword, search_query)
    if not maps_keyword:
        base = (search_query or keyword or "").strip()
        for suffix in (" contact email", " email", " whatsapp", " phone number", " phone"):
            if base.lower().endswith(suffix):
                base = base[: -len(suffix)].strip()
        maps_keyword = (base[:100] if base else "local business").strip()

    maps_location = normalize_location_alias(resolve_scrape_location((location or "").strip()))
    return maps_keyword, maps_location


def _score_title_segment(segment: str, website: str | None = None) -> int:
    score = min(len(segment), 80)
    lower = segment.lower().strip()
    if len(segment) > 70:
        score -= 60
    if lower in GENERIC_TITLE_WORDS or lower in GENERIC_TITLE_SEGMENTS:
        score -= 120
    if is_listicle_or_bad_title(segment):
        score -= 200
    if len(segment) < 3:
        score -= 80
    if re.search(r"[A-Za-z]", segment) and len(segment) >= 4:
        score += 15
    if website:
        host = _host(website).split(".")[0].replace("-", " ").lower()
        seg_norm = re.sub(r"[^a-z0-9]", "", lower)
        host_norm = re.sub(r"[^a-z0-9]", "", host)
        if host_norm and (host_norm in seg_norm or seg_norm in host_norm):
            score += 40
    return score


def extract_business_name_from_title(title: str | None, website: str | None = None) -> str:
    if not title or not title.strip():
        return "Unknown"

    raw = title.strip()
    segments = [s.strip() for s in TITLE_SEPARATOR_PATTERN.split(raw) if s.strip()]
    if not segments:
        return "Unknown"

    if len(segments) == 1:
        best = segments[0]
    else:
        best = max(segments, key=lambda seg: _score_title_segment(seg, website))

    best_score = _score_title_segment(best, website)
    if (best_score < -40 or len(best) > 70) and website:
        host_name = _host(website).split(".")[0].replace("-", " ").title()
        if host_name and len(host_name) > 2 and not is_listicle_or_bad_title(host_name):
            return host_name[:255]

    if _is_bare_domain(best) and website:
        host_name = _host(website).split(".")[0].replace("-", " ").title()
        if host_name and len(host_name) > 2:
            return host_name[:255]

    return best[:255] if best else "Unknown"


def clean_search_title(title: str | None, website: str | None = None) -> str:
    if not title:
        return "Unknown"
    name = extract_business_name_from_title(title, website)
    return name if name else "Unknown"


def has_verified_contact(lead: dict, search_location: str | None = None) -> bool:
    """True when lead has a validated phone or business email."""
    from app.utils.contact_utils import is_junk_email
    from app.utils.phone_lib import phone_matches_search_region

    location_hint = search_location or lead.get("country") or ""
    email = lead.get("email")
    has_email = bool(email and is_valid_email(email) and not is_junk_email(email))

    has_phone = bool(
        lead.get("phone") and format_contact_phone(lead.get("phone"), lead.get("country"))
    )
    if has_phone and location_hint:
        if not phone_matches_search_region(lead.get("phone"), location_hint):
            has_phone = False

    return has_email or has_phone


def is_verified_discovery_lead(lead: dict, search_location: str | None = None) -> bool:
    """Search-snippet leads must have real contact — no title-only junk."""
    if not is_quality_business_lead(lead, search_location):
        return False
    return has_verified_contact(lead, search_location)


def is_quality_business_lead(lead: dict, search_location: str | None = None) -> bool:
    """Reject listicles/directories; keep real businesses with website or contacts."""
    company = (lead.get("company_name") or "").strip()
    if not company or company == "Unknown" or is_listicle_or_bad_title(company):
        return False

    location_hint = search_location or lead.get("country") or ""
    if title_conflicts_with_location(company, location_hint):
        return False

    website = lead.get("website")
    if is_directory_or_aggregator_url(website) or is_listicle_url(website):
        return False

    linkedin = lead.get("linkedin_url")
    facebook = lead.get("facebook_url")
    instagram = lead.get("instagram_url")
    is_meta = lead.get("source") == "meta_ads"
    has_social_page = bool(facebook or instagram)
    notes_lower = (lead.get("notes") or "").lower()
    has_maps_listing = "google maps:" in notes_lower
    if (
        not has_real_website(website)
        and not linkedin
        and not (is_meta and facebook)
        and not (
            lead.get("source") == "web_search" and (has_social_page or has_maps_listing)
        )
    ):
        return False

    from app.utils.contact_utils import is_junk_email

    email = lead.get("email")
    has_email = bool(email and is_valid_email(email))
    if email and is_junk_email(email):
        has_email = False

    has_phone = bool(
        lead.get("phone")
        and format_contact_phone(lead.get("phone"), lead.get("country"))
    )
    if has_phone and location_hint:
        from app.utils.phone_lib import phone_matches_search_region

        if not phone_matches_search_region(lead.get("phone"), location_hint):
            has_phone = False

    maps_phone = bool(
        lead.get("source") == "apify"
        and lead.get("phone")
        and len(re.sub(r"\D", "", str(lead["phone"]))) >= 10
    )

    if has_email or has_phone or maps_phone:
        return True

    # Meta advertisers: page + optional landing URL — enrich later for email/phone
    if is_meta and company and (facebook or has_real_website(website)):
        return True

    # Website-only web leads: pass through so enrichment can crawl contact pages
    if has_real_website(website) and lead.get("source") in ("web_search", "meta_ads"):
        return True

    if linkedin:
        return True

    if has_maps_listing and company and lead.get("source") == "web_search":
        return True

    if lead.get("source") == "web_search" and has_social_page and company:
        return True

    return False


def parse_location_parts(location: str) -> tuple[str | None, str | None]:
    country = infer_country_from_location(location)
    parts = [p.strip() for p in location.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[0], country or parts[-1]
    if parts:
        return parts[0], country
    return None, country


def merge_lead_records(existing: dict, new: dict) -> dict:
    merged = dict(existing)
    for key, value in new.items():
        if value and not merged.get(key):
            merged[key] = value
        elif key == "notes" and value:
            old = merged.get("notes") or ""
            if value not in old:
                merged["notes"] = f"{old}\n{value}".strip() if old else value
    sources = {merged.get("source", ""), new.get("source", "")} - {""}
    if len(sources) > 1:
        merged["source"] = "+".join(sorted(sources))
    return merged


def dedupe_leads(leads: list[dict]) -> list[dict]:
    from app.scraper.utils.dedup import dedupe_leads_production

    return dedupe_leads_production(leads)


def map_no_website_discovery_result(
    item: dict,
    location: str,
    industry_hint: str | None = None,
) -> dict | None:
    """Maps listings and Facebook/Instagram pages — businesses often without their own site."""
    url = item.get("url") or item.get("link") or item.get("website")
    if not url:
        return None
    if not is_google_maps_url(url) and not is_social_only_url(url):
        return None

    raw_title = item.get("title") or item.get("name")
    if is_listicle_or_bad_title(raw_title):
        return None

    title = extract_business_name_from_title(raw_title, url)
    if title == "Unknown" or is_listicle_or_bad_title(title):
        return None

    description = item.get("description") or item.get("snippet") or item.get("text")
    city, country = parse_location_parts(location)
    category = item.get("category") or industry_hint

    lead: dict = {
        "company_name": title,
        "contact_name": None,
        "phone": item.get("phone"),
        "email": item.get("email"),
        "website": None,
        "linkedin_url": None,
        "facebook_url": None,
        "instagram_url": None,
        "address": None,
        "postal_code": None,
        "category": category,
        "city": city,
        "country": country,
        "industry": category,
        "notes": description,
        "source": "web_search",
        "status": LeadStatus.new,
    }

    host = _host(url)
    if "facebook.com" in host or "fb.com" in host:
        lead["facebook_url"] = url
    elif "instagram.com" in host:
        lead["instagram_url"] = url
    elif is_google_maps_url(url):
        lead["notes"] = f"{description or ''}\nGoogle Maps: {url}".strip()

    if description:
        phones = extract_phones_from_snippet(description, country)
        if phones:
            lead["phone"] = pick_best_phone(phones, country)
        emails = extract_emails_from_text(description)
        best_email = pick_best_email(emails)
        if best_email:
            lead["email"] = best_email

    lead = sanitize_lead_contacts(normalize_website_field(lead), search_location=location)
    if not is_quality_business_lead(lead, search_location=location):
        return None
    return lead


def map_web_search_result(
    item: dict,
    location: str,
    industry_hint: str | None = None,
    *,
    discovery_only: bool = False,
) -> dict | None:
    url = item.get("url") or item.get("link") or item.get("website")
    if should_skip_search_url(url):
        return None

    raw_title = item.get("title") or item.get("name")
    if is_listicle_or_bad_title(raw_title):
        return None

    title = extract_business_name_from_title(raw_title, url)
    if title == "Unknown" or is_listicle_or_bad_title(title):
        return None

    description = item.get("description") or item.get("snippet") or item.get("text")
    city, country = parse_location_parts(location)
    category = item.get("category") or industry_hint

    lead: dict = {
        "company_name": title,
        "contact_name": None,
        "phone": item.get("phone"),
        "email": item.get("email"),
        "website": None,
        "linkedin_url": None,
        "facebook_url": None,
        "instagram_url": None,
        "address": None,
        "postal_code": None,
        "category": category,
        "city": city,
        "country": country,
        "industry": category,
        "notes": description,
        "source": "web_search",
        "status": LeadStatus.new,
    }

    if not url:
        return None

    host = _host(url)
    if "linkedin.com" in host and "/company/" in url.lower():
        lead["linkedin_url"] = url
    elif not is_social_only_url(url):
        lead["website"] = url

    if not lead.get("website") and not lead.get("linkedin_url"):
        return None

    if description:
        phones = extract_phones_from_snippet(description, country)
        if phones:
            lead["phone"] = pick_best_phone(phones, country)

        if lead.get("website"):
            emails = extract_emails_from_text(description, lead["website"])
            best_email = pick_best_email(emails, lead["website"])
            if best_email:
                lead["email"] = best_email

    lead = sanitize_lead_contacts(normalize_website_field(lead), search_location=location)
    if discovery_only:
        if not is_verified_discovery_lead(lead, search_location=location):
            return None
        return lead
    if not is_quality_business_lead(lead, search_location=location):
        return None
    return lead


def map_meta_ad_to_lead(item: dict, location: str) -> dict | None:
    """Convert Meta Ad Library row to a lead dict for merge/enrichment."""
    company = _clean_meta_text(
        item.get("company_name") or item.get("advertiser") or item.get("page_name")
    )
    if not company or company == "Unknown" or is_listicle_or_bad_title(company):
        return None

    city, country = parse_location_parts(location)
    industry_hint = item.get("category")
    ad_text = _clean_meta_text(item.get("ad_text") or item.get("body"))
    platforms = item.get("platforms") or []
    platform_note = ""
    if isinstance(platforms, list) and platforms:
        platform_note = f"Platforms: {', '.join(str(p) for p in platforms)}"
    notes_parts = [p for p in (ad_text, platform_note) if p]
    if item.get("is_active") is True:
        notes_parts.insert(0, "Active Meta advertiser")

    website = item.get("website") or item.get("landing_url") or item.get("link_url")
    if website and _is_meta_junk_url(website):
        website = None

    lead: dict = {
        "company_name": company[:255],
        "contact_name": None,
        "phone": None,
        "email": None,
        "website": website,
        "linkedin_url": None,
        "facebook_url": item.get("facebook_url") or item.get("page_url"),
        "instagram_url": item.get("instagram_url"),
        "address": None,
        "postal_code": None,
        "category": industry_hint,
        "city": city,
        "country": country,
        "industry": industry_hint,
        "notes": " | ".join(notes_parts) if notes_parts else "Discovered via Meta Ad Library",
        "source": "meta_ads",
        "status": LeadStatus.new,
    }

    lead = sanitize_lead_contacts(normalize_website_field(lead), search_location=location)
    if not is_quality_business_lead(lead, search_location=location):
        return None
    from app.services.intelligence.meta_enrichment import enrich_meta_ad_lead

    return enrich_meta_ad_lead(lead, item)


def _clean_meta_text(value: str | None) -> str:
    if not value:
        return ""
    return str(value).replace("\\n", " ").strip()


def _is_meta_junk_url(url: str) -> bool:
    host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
    if not host:
        return True
    blocked = (
        "facebook.com",
        "fb.com",
        "instagram.com",
        "fb.me",
        "l.facebook.com",
    )
    return any(b in host for b in blocked)
