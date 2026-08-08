"""Google libphonenumber wrapper for WhatsApp-ready mobile validation."""

from __future__ import annotations

import logging
import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat, PhoneNumberType

logger = logging.getLogger(__name__)

WHATSAPP_NUMBER_TYPES = {
    PhoneNumberType.MOBILE,
    PhoneNumberType.FIXED_LINE_OR_MOBILE,
    PhoneNumberType.PERSONAL_NUMBER,
}

REJECTED_FOR_WHATSAPP = {
    PhoneNumberType.FIXED_LINE,
    PhoneNumberType.UAN,
    PhoneNumberType.PAGER,
}

REJECTED_FOR_CONTACT = {
    PhoneNumberType.UAN,
    PhoneNumberType.PAGER,
}

COUNTRY_TO_REGION: dict[str, str] = {
    "pakistan": "PK",
    "pk": "PK",
    "uae": "AE",
    "united arab emirates": "AE",
    "dubai": "AE",
    "abu dhabi": "AE",
    "sharjah": "AE",
    "saudi arabia": "SA",
    "ksa": "SA",
    "riyadh": "SA",
    "jeddah": "SA",
    "india": "IN",
    "united kingdom": "GB",
    "uk": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "usa": "US",
    "united states": "US",
    "us": "US",
    "germany": "DE",
    "france": "FR",
    "canada": "CA",
    "australia": "AU",
    "qatar": "QA",
    "kuwait": "KW",
    "bahrain": "BH",
    "oman": "OM",
    "turkey": "TR",
    "malaysia": "MY",
    "singapore": "SG",
    "bangladesh": "BD",
    "italy": "IT",
    "spain": "ES",
    "netherlands": "NL",
    "belgium": "BE",
    "switzerland": "CH",
    "austria": "AT",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "ireland": "IE",
    "new zealand": "NZ",
    "south africa": "ZA",
    "nigeria": "NG",
    "kenya": "KE",
    "egypt": "EG",
}

REGION_TO_COUNTRY: dict[str, str] = {
    "PK": "Pakistan",
    "AE": "UAE",
    "SA": "Saudi Arabia",
    "IN": "India",
    "GB": "United Kingdom",
    "US": "United States",
    "DE": "Germany",
    "FR": "France",
    "CA": "Canada",
    "AU": "Australia",
    "QA": "Qatar",
    "KW": "Kuwait",
    "BH": "Bahrain",
    "OM": "Oman",
    "TR": "Turkey",
    "MY": "Malaysia",
    "SG": "Singapore",
    "BD": "Bangladesh",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "BE": "Belgium",
    "CH": "Switzerland",
    "AT": "Austria",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "IE": "Ireland",
    "NZ": "New Zealand",
    "ZA": "South Africa",
    "NG": "Nigeria",
    "KE": "Kenya",
    "EG": "Egypt",
}


def country_to_region(country: str | None) -> str | None:
    if not country:
        return None
    key = country.strip().lower()
    if key in COUNTRY_TO_REGION:
        return COUNTRY_TO_REGION[key]
    for name, region in COUNTRY_TO_REGION.items():
        if name in key or key in name:
            return region
    if len(key) == 2 and key.isalpha():
        return key.upper()
    return None


def region_to_country(region: str | None) -> str | None:
    if not region:
        return None
    return REGION_TO_COUNTRY.get(region.upper())


def infer_country_from_digits(digits: str) -> str | None:
    """Infer country name from E.164 digits (e.g. wa.me/92300... → Pakistan)."""
    clean = re.sub(r"\D", "", digits or "")
    if len(clean) < 10:
        return None
    try:
        parsed = phonenumbers.parse(f"+{clean}", None)
        if phonenumbers.is_valid_number(parsed):
            region = phonenumbers.region_code_for_number(parsed)
            return region_to_country(region)
    except NumberParseException:
        pass
    return None


def _parse_candidates(raw: str, region: str | None) -> phonenumbers.PhoneNumber | None:
    attempts: list[str | None] = []
    if raw.strip().startswith("+"):
        attempts.append(None)
    if region:
        attempts.append(region)
    attempts.append(None)

    seen: set[str | None] = set()
    for attempt in attempts:
        if attempt in seen:
            continue
        seen.add(attempt)
        try:
            parsed = phonenumbers.parse(raw, attempt)
        except NumberParseException:
            continue
        if phonenumbers.is_valid_number(parsed):
            return parsed
    return None


def _accept_mobile_override(parsed: phonenumbers.PhoneNumber) -> bool:
    """Some valid WhatsApp mobiles are misclassified as FIXED_LINE by libphonenumber."""
    if not phonenumbers.is_valid_number(parsed):
        return False
    region = phonenumbers.region_code_for_number(parsed)
    national = str(parsed.national_number)
    if region == "PK" and re.match(r"^3\d{9}$", national):
        return True
    if region == "AE" and re.match(r"^5\d{8}$", national):
        return True
    if region == "GB" and re.match(r"^7\d{9}$", national):
        return True
    if region == "IN" and re.match(r"^[6-9]\d{9}$", national):
        return True
    if region == "DE" and re.match(r"^1[5-7]\d{8,9}$", national):
        return True
    if region == "FR" and re.match(r"^[67]\d{8}$", national):
        return True
    if region == "NL" and re.match(r"^6\d{8}$", national):
        return True
    if region == "ES" and re.match(r"^[67]\d{8}$", national):
        return True
    if region == "IT" and re.match(r"^3\d{8,9}$", national):
        return True
    if region == "IE" and re.match(r"^8[3-9]\d{7}$", national):
        return True
    return False


def normalize_whatsapp_e164(
    phone: str | None,
    country: str | None = None,
    *,
    trust_whatsapp_link: bool = False,
) -> str | None:
    """Validate and format as E.164 (+923001234567) using libphonenumber."""
    if not phone or not str(phone).strip():
        return None

    raw = str(phone).strip()
    # Only prefix + for full international digit strings (not local 03xx / 07xx formats)
    if (
        not raw.startswith("+")
        and raw.isdigit()
        and len(raw) >= 10
        and not raw.startswith("0")
    ):
        raw = f"+{raw}"

    region = country_to_region(country)
    digits_country = infer_country_from_digits(re.sub(r"\D", "", raw))
    if digits_country and not region:
        region = country_to_region(digits_country)

    parsed = _parse_candidates(raw, region)
    if not parsed:
        return None

    number_type = phonenumbers.number_type(parsed)

    if trust_whatsapp_link:
        if phonenumbers.is_valid_number(parsed) and number_type not in REJECTED_FOR_WHATSAPP:
            return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

    if number_type in WHATSAPP_NUMBER_TYPES:
        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

    if _accept_mobile_override(parsed):
        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

    return None


def normalize_contact_e164(phone: str | None, country: str | None = None) -> str | None:
    """Validate and format any usable business phone (mobile or landline) as E.164."""
    if not phone or not str(phone).strip():
        return None

    raw = str(phone).strip()
    if (
        not raw.startswith("+")
        and raw.isdigit()
        and len(raw) >= 10
        and not raw.startswith("0")
    ):
        raw = f"+{raw}"

    region = country_to_region(country)
    digits_country = infer_country_from_digits(re.sub(r"\D", "", raw))
    if digits_country and not region:
        region = country_to_region(digits_country)

    parsed = _parse_candidates(raw, region)
    if not parsed:
        return None

    number_type = phonenumbers.number_type(parsed)
    if number_type in REJECTED_FOR_CONTACT:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


def is_whatsapp_mobile(phone: str | None, country: str | None = None) -> bool:
    return normalize_whatsapp_e164(phone, country) is not None


def is_strict_whatsapp_mobile(phone: str | None, country: str | None = None) -> bool:
    """Stricter check — mobile-capable numbers only (rejects landlines)."""
    e164 = normalize_whatsapp_e164(phone, country)
    if not e164:
        return False
    try:
        parsed = phonenumbers.parse(e164, None)
    except NumberParseException:
        return False
    if not phonenumbers.is_valid_number(parsed):
        return False
    ntype = phonenumbers.number_type(parsed)
    if ntype in WHATSAPP_NUMBER_TYPES:
        return True
    return _accept_mobile_override(parsed)


_COUNTRY_ALIASES: dict[str, str] = {
    "uk": "united kingdom",
    "gb": "united kingdom",
    "england": "united kingdom",
    "scotland": "united kingdom",
    "wales": "united kingdom",
    "uae": "united arab emirates",
    "usa": "united states",
    "us": "united states",
}


def _normalize_country_label(country: str | None) -> str | None:
    if not country:
        return None
    key = country.strip().lower()
    return _COUNTRY_ALIASES.get(key, key)


def phone_matches_search_region(phone: str | None, search_location: str | None) -> bool:
    """True when phone country matches the scrape search location (or location unknown)."""
    if not phone or not search_location:
        return True
    from app.utils.contact_utils import _effective_country_for_phone, infer_country_from_location

    search_country = infer_country_from_location(search_location)
    if not search_country:
        return True
    phone_country = _effective_country_for_phone(phone, search_country)
    if not phone_country:
        return True
    return _normalize_country_label(phone_country) == _normalize_country_label(search_country)


EU_FALLBACK_REGIONS: tuple[str, ...] = (
    "GB",
    "DE",
    "FR",
    "NL",
    "IE",
    "ES",
    "IT",
    "BE",
    "AT",
    "PL",
    "PT",
    "SE",
    "DK",
    "CH",
    "US",
    "PK",
    "AE",
)


def find_numbers_in_text(text: str, country: str | None = None) -> list[str]:
    """Find valid mobile numbers in free text using libphonenumber (single region)."""
    return find_numbers_in_text_multi_region(text, country)


def find_numbers_in_text_multi_region(text: str, country: str | None = None) -> list[str]:
    """Parse phones using the search country only — avoids cross-region false positives."""
    if not text:
        return []
    regions: list[str] = []
    primary = country_to_region(country)
    if primary:
        regions.append(primary)
    else:
        # No location hint: try inferring from explicit + prefixes in text only
        for match in re.finditer(r"\+\d{2,3}[\s\-().]?\d", text):
            prefix_digits = re.sub(r"\D", "", match.group(0))
            inferred = infer_country_from_digits(prefix_digits)
            region = country_to_region(inferred) if inferred else None
            if region and region not in regions:
                regions.append(region)
        if not regions:
            return []

    found: list[str] = []
    seen: set[str] = set()
    for region in regions:
        try:
            for match in phonenumbers.PhoneNumberMatcher(text, region):
                parsed = match.number
                if not phonenumbers.is_valid_number(parsed):
                    continue
                ntype = phonenumbers.number_type(parsed)
                if ntype in WHATSAPP_NUMBER_TYPES or _accept_mobile_override(parsed):
                    e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                    if e164 not in seen:
                        seen.add(e164)
                        found.append(e164)
        except Exception as exc:
            logger.debug("PhoneNumberMatcher failed for %s: %s", region, exc)
    return found
