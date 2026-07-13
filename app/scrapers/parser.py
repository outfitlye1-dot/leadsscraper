import json
import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from app.scrapers.structured_extract import extract_structured_business
from app.utils.contact_utils import (
    extract_emails_from_text,
    extract_facebook_urls,
    extract_instagram_urls,
    extract_linkedin_urls,
    pick_best_email,
)
from app.utils.scrape_sources import (
    clean_search_title,
    extract_business_name_from_title,
    is_listicle_or_bad_title,
    should_skip_search_url,
)

CONTACT_PATH_HINTS = (
    "contact",
    "about",
    "reach",
    "get-in-touch",
    "connect",
    "kontakt",
    "impressum",
    "nous-contacter",
    "contatti",
    "contacto",
    "services",
    "service",
    "pricing",
    "price",
    "menu",
    "book",
    "booking",
    "reservation",
    "order",
    "packages",
    "rates",
)

SCHEMA_TYPE_LABELS = {
    "Restaurant": "Restaurant",
    "FoodEstablishment": "Restaurant",
    "CafeOrCoffeeShop": "Cafe",
    "Bakery": "Bakery",
    "Store": "Retail Store",
    "ClothingStore": "Clothing Store",
    "AutoRepair": "Auto Repair",
    "Dentist": "Dentist",
    "MedicalClinic": "Medical Clinic",
    "Hospital": "Hospital",
    "LegalService": "Legal Services",
    "Attorney": "Legal Services",
    "RealEstateAgent": "Real Estate",
    "TravelAgency": "Travel Agency",
    "Hotel": "Hotel",
    "LodgingBusiness": "Hotel",
    "BeautySalon": "Beauty Salon",
    "HairSalon": "Hair Salon",
    "Gym": "Gym",
    "HealthClub": "Gym",
    "ProfessionalService": "Professional Services",
    "LocalBusiness": "Local Business",
    "Organization": "Business",
    "Corporation": "Business",
}


def unwrap_search_url(url: str) -> str:
    if not url:
        return url
    url = url.strip()
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "duckduckgo.com" in host and "/l/" in parsed.path:
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
    return url


def parse_duckduckgo_results(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    for block in soup.select("div.result"):
        link = block.select_one("a.result__a")
        snippet = block.select_one("a.result__snippet, div.result__snippet")
        if not link:
            continue
        url = unwrap_search_url(link.get("href") or "")
        title = link.get_text(strip=True)
        description = snippet.get_text(strip=True) if snippet else None
        if url and not should_skip_search_url(url):
            results.append({"title": title, "url": url, "description": description})

    if results:
        return results

    for link in soup.select("a.result__a"):
        url = unwrap_search_url(link.get("href") or "")
        title = link.get_text(strip=True)
        if url and not should_skip_search_url(url):
            results.append({"title": title, "url": url, "description": None})

    return results


def _schema_types(item: dict) -> list[str]:
    item_type = item.get("@type") or ""
    if isinstance(item_type, list):
        return [str(t) for t in item_type]
    return [str(item_type)] if item_type else []


def _schema_category_label(item: dict) -> str | None:
    for key in ("category", "serviceType", "priceRange"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:255]
        if isinstance(value, list) and value and isinstance(value[0], str):
            return value[0].strip()[:255]

    for schema_type in _schema_types(item):
        if schema_type in SCHEMA_TYPE_LABELS:
            return SCHEMA_TYPE_LABELS[schema_type]
    return None


def extract_schema_org_metadata(soup: BeautifulSoup) -> dict:
    name: str | None = None
    category: str | None = None
    telephone: str | None = None
    contact_name: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    postal_code: str | None = None

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        queue: list = data if isinstance(data, list) else [data]
        seen_ids: set[int] = set()

        while queue:
            item = queue.pop(0)
            if not isinstance(item, dict):
                continue
            item_id = id(item)
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            graph = item.get("@graph")
            if isinstance(graph, list):
                queue.extend(graph)

            types = _schema_types(item)
            is_business = any(
                t in SCHEMA_TYPE_LABELS or t.endswith("Business") or t.endswith("Store")
                for t in types
            )
            if is_business or item.get("telephone") or item.get("phone"):
                if not name:
                    raw_name = item.get("name")
                    if raw_name and isinstance(raw_name, str):
                        cleaned = extract_business_name_from_title(raw_name)
                        if cleaned != "Unknown" and not is_listicle_or_bad_title(cleaned):
                            name = cleaned
                if not category:
                    category = _schema_category_label(item)
                if not telephone:
                    for key in ("telephone", "phone", "mobileNumber"):
                        value = item.get(key)
                        if isinstance(value, str) and value.strip():
                            telephone = value.strip()
                            break
                        if isinstance(value, list) and value and isinstance(value[0], str):
                            telephone = value[0].strip()
                            break
                if not contact_name:
                    founder = item.get("founder") or item.get("employee")
                    if isinstance(founder, dict) and founder.get("name"):
                        contact_name = str(founder["name"]).strip()[:255]
                    elif isinstance(founder, str) and founder.strip():
                        contact_name = founder.strip()[:255]
                if not address:
                    addr = item.get("address")
                    if isinstance(addr, str) and addr.strip():
                        address = addr.strip()[:500]
                    elif isinstance(addr, dict):
                        street = addr.get("streetAddress") or addr.get("street")
                        locality = addr.get("addressLocality")
                        region = addr.get("addressRegion")
                        parts = [
                            p
                            for p in (street, locality, region)
                            if isinstance(p, str) and p.strip()
                        ]
                        if parts:
                            address = ", ".join(parts)[:500]
                        if isinstance(locality, str) and locality.strip():
                            city = locality.strip()[:100]
                        postal = addr.get("postalCode")
                        if isinstance(postal, str) and postal.strip():
                            postal_code = postal.strip()[:20]
                        addr_country = addr.get("addressCountry")
                        if isinstance(addr_country, str) and addr_country.strip():
                            country = addr_country.strip()[:100]

    return {
        "schema_name": name,
        "category": category,
        "telephone": telephone,
        "contact_name": contact_name,
        "address": address,
        "city": city,
        "country": country,
        "postal_code": postal_code,
    }


def extract_og_site_name(soup: BeautifulSoup) -> str | None:
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content"):
        cleaned = extract_business_name_from_title(og["content"].strip())
        if cleaned != "Unknown" and not is_listicle_or_bad_title(cleaned):
            return cleaned
    return None


def extract_brand_h1(soup: BeautifulSoup, website: str | None = None) -> str | None:
    for h1 in soup.find_all("h1"):
        text = h1.get_text(strip=True)
        if not text or len(text) > 80:
            continue
        classes = " ".join(h1.get("class") or []).lower()
        if any(token in classes for token in ("logo", "brand", "site-title", "company")):
            cleaned = extract_business_name_from_title(text, website)
            if cleaned != "Unknown" and not is_listicle_or_bad_title(cleaned):
                return cleaned
    first_h1 = soup.find("h1")
    if first_h1:
        text = first_h1.get_text(strip=True)
        if text and 3 <= len(text) <= 60:
            cleaned = extract_business_name_from_title(text, website)
            if cleaned != "Unknown" and not is_listicle_or_bad_title(cleaned):
                return cleaned
    return None


def extract_page_title(soup: BeautifulSoup, website: str | None = None) -> str:
    og_site = extract_og_site_name(soup)
    if og_site:
        return og_site

    if soup.title and soup.title.string:
        return extract_business_name_from_title(soup.title.string, website)

    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return extract_business_name_from_title(og["content"], website)

    brand_h1 = extract_brand_h1(soup, website)
    if brand_h1:
        return brand_h1

    return "Unknown"


def extract_category_from_html(
    soup: BeautifulSoup, industry_hint: str | None = None
) -> str | None:
    schema = extract_schema_org_metadata(soup)
    if schema.get("category"):
        return schema["category"]

    keywords = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
    if keywords and keywords.get("content"):
        first = keywords["content"].split(",")[0].strip()
        if first and len(first) >= 3:
            return first[:255].title()

    article_section = soup.find("meta", property="article:section")
    if article_section and article_section.get("content"):
        return article_section["content"].strip()[:255].title()

    return industry_hint


def find_contact_links(soup: BeautifulSoup, base_url: str, max_links: int = 2) -> list[str]:
    base_host = urlparse(base_url).netloc.lower()
    found: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if parsed.netloc.lower() != base_host:
            continue
        path = parsed.path.lower()
        text = anchor.get_text(strip=True).lower()
        if any(hint in path or hint in text for hint in CONTACT_PATH_HINTS):
            if full_url not in found:
                found.append(full_url)
        if len(found) >= max_links:
            break

    return found


def extract_contacts_from_html(
    html: str, url: str, country: str | None = None, industry_hint: str | None = None
) -> dict:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    raw_html = str(soup)
    website = url

    schema = extract_schema_org_metadata(soup)
    structured = extract_structured_business(html, url)

    if structured.get("site_name") and not schema.get("schema_name"):
        schema["schema_name"] = structured["site_name"]
    if structured.get("name") and not schema.get("schema_name"):
        schema["schema_name"] = structured["name"]
    if structured.get("category") and not schema.get("category"):
        schema["category"] = structured["category"]
    if structured.get("telephone") and not schema.get("telephone"):
        schema["telephone"] = structured["telephone"]
    for field in ("contact_name", "address", "city", "country", "postal_code"):
        if structured.get(field) and not schema.get(field):
            schema[field] = structured[field]

    emails = extract_emails_from_text(text, website) or extract_emails_from_text(raw_html, website)
    if structured.get("email"):
        email = structured["email"].lower()
        if email not in emails:
            emails.insert(0, email)
    linkedin = extract_linkedin_urls(raw_html)
    instagram = extract_instagram_urls(raw_html)
    facebook = extract_facebook_urls(raw_html)
    page_country = schema.get("country") or country
    from app.utils.phone_confidence import PhoneHit, aggregate_phone_hits
    from app.utils.phone_extract import extract_phone_hits_from_html

    phone_hits = extract_phone_hits_from_html(raw_html, page_country)
    if structured.get("telephone"):
        schema_hit = PhoneHit(
            raw=structured["telephone"], source="schema_org", country=page_country
        )
        if schema_hit.resolved_e164():
            phone_hits.append(schema_hit)
    if schema.get("telephone"):
        schema_hit = PhoneHit(raw=schema["telephone"], source="schema_org", country=page_country)
        if schema_hit.resolved_e164():
            phone_hits.append(schema_hit)

    best_phone = aggregate_phone_hits(phone_hits, page_country)

    mailto = soup.select_one('a[href^="mailto:"]')
    if mailto:
        email = mailto["href"].replace("mailto:", "").split("?")[0].strip().lower()
        if email and email not in emails:
            emails.insert(0, email)

    best_email = pick_best_email(emails, website)

    return {
        "title": extract_page_title(soup, website),
        "schema_name": schema.get("schema_name"),
        "og_site_name": extract_og_site_name(soup),
        "brand_h1": extract_brand_h1(soup, website),
        "category": schema.get("category") or extract_category_from_html(soup, industry_hint),
        "email": best_email,
        "phone": best_phone,
        "contact_name": schema.get("contact_name"),
        "address": schema.get("address"),
        "city": schema.get("city"),
        "country": schema.get("country"),
        "postal_code": schema.get("postal_code"),
        "linkedin_url": linkedin[0] if linkedin else None,
        "facebook_url": facebook[0] if facebook else None,
        "instagram_url": instagram[0] if instagram else None,
        "description": _meta_description(soup),
    }


def _meta_description(soup: BeautifulSoup) -> str | None:
    meta = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if meta and meta.get("content"):
        return meta["content"].strip()[:500]
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return og["content"].strip()[:500]
    return None
