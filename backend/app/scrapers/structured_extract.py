"""Structured page extraction via extruct + trafilatura."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _is_bare_domain(name: str) -> bool:
    import re

    return bool(re.match(r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$", name.strip().lower()))


BUSINESS_SCHEMA_TYPES = {
    "Organization",
    "LocalBusiness",
    "Corporation",
    "Store",
    "Restaurant",
    "FoodEstablishment",
    "ProfessionalService",
    "MedicalBusiness",
    "LegalService",
    "FinancialService",
    "RealEstateAgent",
    "TravelAgency",
    "LodgingBusiness",
    "Hotel",
    "AutoRepair",
    "BeautySalon",
    "HealthClub",
    "Dentist",
    "MedicalClinic",
}

SCHEMA_TYPE_LABELS = {
    "Restaurant": "Restaurant",
    "FoodEstablishment": "Restaurant",
    "Store": "Retail Store",
    "AutoRepair": "Auto Repair",
    "Dentist": "Dentist",
    "MedicalClinic": "Medical Clinic",
    "Hotel": "Hotel",
    "LodgingBusiness": "Hotel",
    "BeautySalon": "Beauty Salon",
    "RealEstateAgent": "Real Estate",
    "TravelAgency": "Travel Agency",
    "LegalService": "Legal Services",
    "ProfessionalService": "Professional Services",
    "LocalBusiness": "Local Business",
    "Organization": "Business",
    "Corporation": "Business",
}


def _schema_types(item: dict) -> list[str]:
    item_type = item.get("@type") or ""
    if isinstance(item_type, list):
        return [str(t).split("/")[-1] for t in item_type]
    if isinstance(item_type, str):
        return [item_type.split("/")[-1]]
    return []


def _is_business_item(item: dict) -> bool:
    types = _schema_types(item)
    return any(
        t in BUSINESS_SCHEMA_TYPES or t.endswith("Business") or t.endswith("Store") for t in types
    )


def _category_from_item(item: dict) -> str | None:
    for key in ("category", "serviceType"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:255]
        if isinstance(value, list) and value and isinstance(value[0], str):
            return value[0].strip()[:255]
    for schema_type in _schema_types(item):
        if schema_type in SCHEMA_TYPE_LABELS:
            return SCHEMA_TYPE_LABELS[schema_type]
    return None


def _telephone_from_item(item: dict) -> str | None:
    for key in ("telephone", "phone", "mobileNumber"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value and isinstance(value[0], str):
            return value[0].strip()
    return None


def _contact_name_from_item(item: dict) -> str | None:
    for key in ("founder", "employee", "author"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:255]
        if isinstance(value, dict):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()[:255]
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, str) and first.strip():
                return first.strip()[:255]
            if isinstance(first, dict):
                name = first.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()[:255]

    contact_point = item.get("contactPoint")
    points = contact_point if isinstance(contact_point, list) else [contact_point]
    for point in points:
        if not isinstance(point, dict):
            continue
        name = point.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()[:255]
    return None


def _address_from_item(item: dict) -> dict[str, str | None]:
    result = {"address": None, "city": None, "country": None, "postal_code": None}
    addr = item.get("address")
    if isinstance(addr, str) and addr.strip():
        result["address"] = addr.strip()[:500]
        return result
    if not isinstance(addr, dict):
        return result

    street = addr.get("streetAddress") or addr.get("street")
    locality = addr.get("addressLocality") or addr.get("city")
    region = addr.get("addressRegion")
    postal = addr.get("postalCode")
    country = addr.get("addressCountry")

    parts = [p for p in (street, locality, region) if isinstance(p, str) and p.strip()]
    if parts:
        result["address"] = ", ".join(parts)[:500]
    if isinstance(locality, str) and locality.strip():
        result["city"] = locality.strip()[:100]
    if isinstance(postal, str) and postal.strip():
        result["postal_code"] = postal.strip()[:20]
    if isinstance(country, str) and country.strip():
        result["country"] = country.strip()[:100]
    return result


def _walk_json_ld(nodes: list[Any]) -> dict:
    result = {
        "name": None,
        "telephone": None,
        "category": None,
        "email": None,
        "contact_name": None,
        "address": None,
        "city": None,
        "country": None,
        "postal_code": None,
    }
    queue: list[Any] = list(nodes)
    seen: set[int] = set()

    while queue:
        item = queue.pop(0)
        if not isinstance(item, dict):
            continue
        item_id = id(item)
        if item_id in seen:
            continue
        seen.add(item_id)

        graph = item.get("@graph")
        if isinstance(graph, list):
            queue.extend(graph)

        if _is_business_item(item) or item.get("telephone") or item.get("phone"):
            if not result["name"]:
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    result["name"] = name.strip()[:255]
            if not result["telephone"]:
                result["telephone"] = _telephone_from_item(item)
            if not result["category"]:
                result["category"] = _category_from_item(item)
            if not result["email"]:
                email = item.get("email")
                if isinstance(email, str) and email.strip():
                    result["email"] = email.strip().lower()
            if not result["contact_name"]:
                result["contact_name"] = _contact_name_from_item(item)
            if not result["address"]:
                addr_fields = _address_from_item(item)
                for key, value in addr_fields.items():
                    if value and not result.get(key):
                        result[key] = value

    return result


def extract_structured_business(html: str, url: str) -> dict:
    """Extract business fields from JSON-LD / OpenGraph / microdata."""
    result = {
        "name": None,
        "telephone": None,
        "category": None,
        "email": None,
        "site_name": None,
        "contact_name": None,
        "address": None,
        "city": None,
        "country": None,
        "postal_code": None,
    }
    if not html:
        return result

    try:
        import extruct
        from w3lib.html import get_base_url

        base_url = get_base_url(html, url)
        data = extruct.extract(
            html,
            base_url=base_url,
            syntaxes=["json-ld", "opengraph", "microdata"],
        )

        json_ld = data.get("json-ld") or []
        if json_ld:
            merged = _walk_json_ld(json_ld if isinstance(json_ld, list) else [json_ld])
            for key, value in merged.items():
                if value and not result.get(key):
                    result[key] = value

        opengraph = data.get("opengraph") or []
        if opengraph and isinstance(opengraph, list):
            og = opengraph[0] if opengraph else {}
            if isinstance(og, dict):
                if not result["name"] and og.get("title"):
                    result["name"] = str(og["title"]).strip()[:255]
                if not result["site_name"] and og.get("site_name"):
                    result["site_name"] = str(og["site_name"]).strip()[:255]

        microdata = data.get("microdata") or []
        for item in microdata:
            if not isinstance(item, dict):
                continue
            props = item.get("properties") or {}
            item_type = str(item.get("type") or "")
            if "business" not in item_type.lower() and "organization" not in item_type.lower():
                continue
            if not result["name"] and props.get("name"):
                result["name"] = str(props["name"][0] if isinstance(props["name"], list) else props["name"]).strip()[:255]
            if not result["telephone"] and props.get("telephone"):
                tel = props["telephone"]
                result["telephone"] = str(tel[0] if isinstance(tel, list) else tel).strip()
    except Exception as exc:
        logger.debug("extruct extraction failed for %s: %s", url, exc)

    try:
        import trafilatura

        metadata = trafilatura.extract_metadata(html, default_url=url)
        if metadata:
            if not result["name"] and metadata.title:
                title = metadata.title.strip()
                if title and not _is_bare_domain(title):
                    result["name"] = title[:255]
            sitename = getattr(metadata, "sitename", None)
            if not result["site_name"] and sitename:
                sitename = sitename.strip()
                if sitename and not _is_bare_domain(sitename):
                    result["site_name"] = sitename[:255]
    except Exception as exc:
        logger.debug("trafilatura metadata failed for %s: %s", url, exc)

    return result
