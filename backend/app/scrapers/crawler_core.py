from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.scraper.logging.scrape_logger import log_lead_parsed, log_lead_rejected
from app.scraper.metrics import ScrapeMetrics
from app.scraper.validators.quality import apply_quality_to_lead
from app.scrapers.fetcher import PageFetcher
from app.scrapers.parser import extract_contacts_from_html, find_contact_links
from app.utils.lead_contacts import sanitize_lead_contacts
from app.utils.phone_confidence import PhoneHit, aggregate_phone_hits
from app.utils.phone_extract import extract_phone_hits_from_html
from app.utils.scrape_sources import (
    extract_business_name_from_title,
    is_listicle_or_bad_title,
    is_quality_business_lead,
    parse_location_parts,
)


def _merge_contacts(base: dict, extra: dict) -> dict:
    merged = dict(base)
    for key in (
        "email",
        "linkedin_url",
        "facebook_url",
        "instagram_url",
        "description",
        "category",
        "contact_name",
        "address",
        "city",
        "country",
        "postal_code",
    ):
        if not merged.get(key) and extra.get(key):
            merged[key] = extra[key]
    return merged


def _has_phone(contacts: dict) -> bool:
    return bool(contacts.get("phone"))


def _score_name_candidate(name: str, website: str | None, source_weight: int) -> int:
    if not name or name == "Unknown" or is_listicle_or_bad_title(name):
        return -1000
    if len(name) > 70:
        return -1000
    lower = name.lower().strip()
    if lower in {"united kingdom", "uk", "london", "england", "united states", "usa"}:
        return -1000
    score = source_weight + min(len(name), 60)
    if len(name) > 50:
        score -= 30
    if "best" in lower or "welcome" in lower or "official" in lower:
        score -= 70
    if website:
        host = urlparse(website).netloc.lower().split(".")[0].replace("-", "")
        norm = name.lower().replace(" ", "").replace("-", "")
        if host and (host in norm or norm in host):
            score += 40
        elif host and ("best" in lower or "welcome" in lower):
            # Prefer host brand over marketing slogans
            score -= 40
    return score


def _pick_company_name(contacts: dict, seed_title: str | None, host: str, website: str | None) -> str | None:
    candidates: list[tuple[int, str]] = []
    host_base = host.split(".")[0].replace("-", " ").title() if host else ""

    for name, weight in (
        (contacts.get("og_site_name"), 100),
        (contacts.get("schema_name"), 90),
        (contacts.get("brand_h1"), 80),
        (extract_business_name_from_title(seed_title, website) if seed_title else None, 75),
        (contacts.get("title"), 50),
        (host_base, 45),
    ):
        if not name:
            continue
        cleaned = extract_business_name_from_title(name, website)
        if cleaned != "Unknown" and not is_listicle_or_bad_title(cleaned):
            from app.utils.scrape_sources import _is_bare_domain, GENERIC_TITLE_WORDS

            if _is_bare_domain(cleaned):
                continue
            if cleaned.lower().strip() in GENERIC_TITLE_WORDS:
                continue
            score = _score_name_candidate(cleaned, website, weight)
            if score > -500:
                candidates.append((score, cleaned))

    if candidates:
        return max(candidates, key=lambda item: item[0])[1]

    cleaned_host = extract_business_name_from_title(host_base, website)
    if cleaned_host and cleaned_host != "Unknown" and _score_name_candidate(cleaned_host, website, 40) > -500:
        return cleaned_host
    return None


def _verified_phone_from_pages(
    html_pages: list[str],
    country: str | None,
    seed_description: str | None = None,
) -> str | None:
    hits: list[PhoneHit] = []
    for page_html in html_pages:
        hits.extend(extract_phone_hits_from_html(page_html, country))

    if seed_description:
        from app.utils.contact_utils import extract_phones_from_snippet

        for phone in extract_phones_from_snippet(seed_description, country):
            hits.append(
                PhoneHit(raw=phone, source="search_snippet", country=country, from_whatsapp=True)
            )

    return aggregate_phone_hits(hits, country)


def scrape_business_site(
    fetcher: PageFetcher,
    url: str,
    seed_title: str | None,
    location: str,
    seed_description: str | None = None,
    industry_hint: str | None = None,
    metrics: ScrapeMetrics | None = None,
) -> dict | None:
    html, final_url = fetcher.fetch(url)
    host = urlparse(url).netloc.lower() or urlparse(final_url).netloc.lower()
    city, search_country = parse_location_parts(location)
    country = search_country
    website = final_url or url

    if not html:
        if seed_title and not is_listicle_or_bad_title(seed_title):
            company = extract_business_name_from_title(seed_title, website)
            phone = _verified_phone_from_pages([], country, seed_description)
            lead = apply_quality_to_lead(
                {
                    "company_name": company,
                    "website": website,
                    "email": None,
                    "phone": phone,
                    "linkedin_url": None,
                    "instagram_url": None,
                    "facebook_url": None,
                    "contact_name": None,
                    "address": None,
                    "city": city,
                    "category": industry_hint,
                    "industry": industry_hint,
                    "notes": seed_description,
                    "source": "web_search",
                    "country": country,
                }
            )
            result = sanitize_lead_contacts(lead, search_location=location)
            if is_quality_business_lead(result, search_location=location):
                log_lead_parsed(metrics, result.get("company_name", ""))
                return result
            log_lead_rejected(metrics, url, "quality gate (no HTML)")
        return None

    html_pages = [html]
    contacts = extract_contacts_from_html(html, final_url, country, industry_hint)

    from app.core.config import get_settings as _cfg
    from app.scrapers.ai_selectors import discover_selectors_from_html
    from app.scrapers.image_intel import extract_images

    settings = _cfg()
    if settings.SCRAPER_AI_SELECTORS and not settings.SCRAPER_FAST_MODE:
        discover_selectors_from_html(html, final_url)
    if not settings.SCRAPER_FAST_MODE:
        images = extract_images(html, final_url)
        if images.logo_url and metrics:
            metrics.inc("images_downloaded", len(images.images))
        if images.logo_url:
            contacts["logo_url"] = images.logo_url

    page_country = contacts.get("country") or country

    has_primary_contact = bool(contacts.get("email")) or _has_phone(contacts)
    skip_contact_pages = settings.SCRAPER_FAST_MODE and has_primary_contact

    if not skip_contact_pages:
        soup = BeautifulSoup(html, "lxml")
        max_links = 3 if not settings.SCRAPER_FAST_MODE else 1
        for link in find_contact_links(soup, final_url, max_links=max_links):
            if fetcher.job_control and fetcher.job_control():
                break
            extra_html, extra_url = fetcher.fetch(link)
            if extra_html:
                html_pages.append(extra_html)
                extra = extract_contacts_from_html(extra_html, extra_url, page_country, industry_hint)
                contacts = _merge_contacts(contacts, extra)
                if extra.get("country"):
                    page_country = extra["country"]
                if settings.SCRAPER_FAST_MODE and (
                    contacts.get("email") or _has_phone(contacts)
                ):
                    break

    verified_phone = _verified_phone_from_pages(html_pages, page_country, seed_description)
    if verified_phone:
        contacts["phone"] = verified_phone

    company_name = _pick_company_name(contacts, seed_title, host, website)
    if not company_name:
        log_lead_rejected(metrics, url, "no company name")
        return None

    category = contacts.get("category") or industry_hint

    result = sanitize_lead_contacts(
        apply_quality_to_lead(
            {
                "company_name": company_name,
                "contact_name": contacts.get("contact_name"),
                "website": final_url,
                "email": contacts.get("email"),
                "phone": contacts.get("phone"),
                "linkedin_url": contacts.get("linkedin_url"),
                "instagram_url": contacts.get("instagram_url"),
                "facebook_url": contacts.get("facebook_url"),
                "address": contacts.get("address"),
                "postal_code": contacts.get("postal_code"),
                "city": contacts.get("city") or city,
                "country": page_country,
                "category": category,
                "industry": category,
                "notes": contacts.get("description") or seed_description,
                "source": "web_search",
            }
        ),
        search_location=location,
    )
    if not is_quality_business_lead(result, search_location=location):
        log_lead_rejected(metrics, url, "quality gate")
        return None
    log_lead_parsed(metrics, company_name)
    return result
