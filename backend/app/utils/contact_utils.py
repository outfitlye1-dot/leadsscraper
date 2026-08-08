import logging
import re
from functools import lru_cache
from urllib.parse import urlparse

from email_validator import EmailNotValidError, validate_email

from app.utils import phone_lib
from app.utils.scrape_defaults import EUROPE_CITY_COUNTRY

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
OBFUSCATED_EMAIL_PATTERN = re.compile(
    r"([a-zA-Z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\s+at\s+|\s*@\s*)\s*([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)
LINKEDIN_PATTERN = re.compile(
    r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9_\-/%]+",
    re.IGNORECASE,
)
INSTAGRAM_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?",
    re.IGNORECASE,
)
FACEBOOK_PATTERN = re.compile(
    r"https?://(?:www\.)?facebook\.com/(?!sharer|share|dialog|plugins|tr)[a-zA-Z0-9._\-/]+/?",
    re.IGNORECASE,
)
WA_ME_PATTERN = re.compile(r"wa\.me/(\d{10,15})", re.IGNORECASE)
WHATSAPP_SEND_PATTERN = re.compile(
    r"(?:whatsapp\.com/send|api\.whatsapp\.com/send|whatsapp://send)[^\"'\s>]*[?&]phone=(\d{10,15})",
    re.IGNORECASE,
)
WHATSAPP_PHONE_PARAM_PATTERN = re.compile(r"[?&]phone=(\d{10,15})", re.IGNORECASE)
WEB_WHATSAPP_PATTERN = re.compile(
    r"web\.whatsapp\.com/send[^\"'\s>]*[?&]phone=(\d{10,15})",
    re.IGNORECASE,
)
TEL_HREF_PATTERN = re.compile(r"tel:([+\d\s\-().]+)", re.IGNORECASE)
PK_MOBILE_TEXT_PATTERN = re.compile(
    r"(?:"
    r"(?:\+?92|0092|92[\s\-().]?|0)(3[0-9]{2})[\s\-().]?\d{7}"
    r"|"
    r"(?<!\d)(3[0-9]{2})[\s\-().]?\d{7}(?!\d)"
    r")",
    re.IGNORECASE,
)
UAE_MOBILE_TEXT_PATTERN = re.compile(
    r"(?:"
    r"(?:\+?971|00971|971[\s\-().]?|0)(5[0-9])[\s\-().]?\d{7}"
    r"|"
    r"(?<!\d)(5[0-9]{2})[\s\-().]?\d{6}(?!\d)"
    r")",
    re.IGNORECASE,
)
UK_MOBILE_TEXT_PATTERN = re.compile(
    r"(?:"
    r"(?:\+?44|0044|44[\s\-().]?|0)7\d{3}[\s\-().]?\d{6}"
    r"|"
    r"(?<!\d)07\d{3}[\s\-().]?\d{6}(?!\d)"
    r")",
    re.IGNORECASE,
)
EU_DE_MOBILE_PATTERN = re.compile(
    r"(?:\+?49|0049|49[\s\-().]?|0)(1[5-7]\d)[\s\-().]?\d{7,8}",
    re.IGNORECASE,
)
EU_FR_MOBILE_PATTERN = re.compile(
    r"(?:\+?33|0033|33[\s\-().]?|0)[67][\s\-().]?\d{2}[\s\-().]?\d{2}[\s\-().]?\d{2}[\s\-().]?\d{2}",
    re.IGNORECASE,
)
EU_NL_MOBILE_PATTERN = re.compile(
    r"(?:\+?31|0031|31[\s\-().]?|0)6[\s\-().]?\d{8}",
    re.IGNORECASE,
)
EU_IE_MOBILE_PATTERN = re.compile(
    r"(?:\+?353|00353|353[\s\-().]?|0)8[3-9][\s\-().]?\d{7}",
    re.IGNORECASE,
)
EU_ES_MOBILE_PATTERN = re.compile(
    r"(?:\+?34|0034|34[\s\-().]?|0)[67][\s\-().]?\d{2}[\s\-().]?\d{2}[\s\-().]?\d{2}[\s\-().]?\d{2}",
    re.IGNORECASE,
)
EU_IT_MOBILE_PATTERN = re.compile(
    r"(?:\+?39|0039|39[\s\-().]?|0)3\d{2}[\s\-().]?\d{6,7}",
    re.IGNORECASE,
)
WHATSAPP_LABEL_PATTERN = re.compile(
    r"whatsapp(?:\s*(?:no|number|#|:))?\s*[:\-]?\s*([+\d\s\-().]{10,18})",
    re.IGNORECASE,
)
# Tighter than generic — requires + or leading 0 or country code hint
PHONE_PATTERN = re.compile(
    r"(?:\+\d{1,3}[\s\-().]?\d{2,4}[\s\-().]?\d{3,4}[\s\-().]?\d{3,4}|0\d{2,4}[\s\-().]?\d{6,8})"
)

WHATSAPP_DIGIT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^923[0-9]{9}$"), "Pakistan"),
    (re.compile(r"^9715[0-9]{8}$"), "UAE"),
    (re.compile(r"^9665[0-9]{8}$"), "Saudi Arabia"),
    (re.compile(r"^91[6-9][0-9]{9}$"), "India"),
    (re.compile(r"^447[0-9]{9}$"), "United Kingdom"),
    (re.compile(r"^491[5-7][0-9]{8,9}$"), "Germany"),
    (re.compile(r"^336[0-9]{8}$"), "France"),
    (re.compile(r"^337[0-9]{8}$"), "France"),
    (re.compile(r"^316[0-9]{8}$"), "Netherlands"),
    (re.compile(r"^3538[0-9]{8}$"), "Ireland"),
    (re.compile(r"^346[0-9]{8}$"), "Spain"),
    (re.compile(r"^347[0-9]{8}$"), "Spain"),
    (re.compile(r"^393[0-9]{8,9}$"), "Italy"),
    (re.compile(r"^1[2-9][0-9]{9}$"), "United States"),
)

COUNTRY_PHONE_CODES: dict[str, str] = {
    "pakistan": "92",
    "pk": "92",
    "uae": "971",
    "united arab emirates": "971",
    "dubai": "971",
    "abu dhabi": "971",
    "saudi arabia": "966",
    "ksa": "966",
    "india": "91",
    "united kingdom": "44",
    "uk": "44",
    "england": "44",
    "germany": "49",
    "de": "49",
    "france": "33",
    "fr": "33",
    "netherlands": "31",
    "nl": "31",
    "spain": "34",
    "es": "34",
    "italy": "39",
    "it": "39",
    "ireland": "353",
    "ie": "353",
    "belgium": "32",
    "austria": "43",
    "switzerland": "41",
    "sweden": "46",
    "norway": "47",
    "denmark": "45",
    "finland": "358",
    "poland": "48",
    "portugal": "351",
    "czech republic": "420",
    "romania": "40",
    "greece": "30",
    "usa": "1",
    "united states": "1",
    "us": "1",
}

CITY_COUNTRY_HINTS: dict[str, str] = {
    **EUROPE_CITY_COUNTRY,
    "karachi": "Pakistan",
    "lahore": "Pakistan",
    "islamabad": "Pakistan",
    "rawalpindi": "Pakistan",
    "faisalabad": "Pakistan",
    "multan": "Pakistan",
    "peshawar": "Pakistan",
    "quetta": "Pakistan",
    "sialkot": "Pakistan",
    "dubai": "UAE",
    "abu dhabi": "UAE",
    "sharjah": "UAE",
    "riyadh": "Saudi Arabia",
    "jeddah": "Saudi Arabia",
    "mumbai": "India",
    "delhi": "India",
    "london": "United Kingdom",
}

JUNK_EMAIL_DOMAINS = {
    "example.com",
    "test.com",
    "email.com",
    "domain.com",
    "yourdomain.com",
    "yoursite.com",
    "sentry.io",
    "w3.org",
    "schema.org",
    "googleapis.com",
    "gstatic.com",
    "cloudflare.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "github.com",
    "localhost",
    "wixpress.com",
    "squarespace.com",
    "myshopify.com",
    "godaddy.com",
    "placeholder.com",
    "sample.com",
    "bootstrap.com",
    "jquery.com",
    "webpack.js.org",
    "2x.png",
    "3x.png",
}

JUNK_EMAIL_LOCAL_PARTS = {
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "mailer-daemon",
    "postmaster",
    "webmaster",
    "hostmaster",
    "abuse",
    "bounce",
    "unsubscribe",
    "newsletter",
    "news",
}

BUSINESS_EMAIL_LOCAL_PREFIXES = (
    "info@",
    "contact@",
    "hello@",
    "sales@",
    "support@",
    "enquiry@",
    "inquiry@",
    "office@",
    "admin@",
    "business@",
)

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "icloud.com",
    "protonmail.com",
    "ymail.com",
}


def _email_domain(email: str) -> str:
    return email.split("@")[-1].lower().strip()


def _website_host(website: str | None) -> str:
    if not website:
        return ""
    try:
        host = urlparse(website if "://" in website else f"https://{website}").netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def is_junk_email(email: str) -> bool:
    email = email.lower().strip()
    local, _, domain = email.partition("@")
    if not local or not domain:
        return True
    if domain in JUNK_EMAIL_DOMAINS:
        return True
    if any(domain.endswith(f".{junk}") for junk in JUNK_EMAIL_DOMAINS):
        return True
    if "sentry" in domain:
        return True
    if domain.endswith((".systems", ".internal", ".local")):
        return True
    if local in JUNK_EMAIL_LOCAL_PARTS:
        return True
    if re.fullmatch(r"[0-9a-f]{32}", local):
        return True
    if email.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
        return True
    if re.search(r"\d{3,}x\d{3,}", email):
        return True
    return False


def is_valid_email(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    email = value.strip().lower()
    if is_junk_email(email):
        return False
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def email_matches_website(email: str, website: str | None) -> bool:
    host = _website_host(website)
    if not host:
        return False
    domain = _email_domain(email)
    return domain == host or domain.endswith(f".{host}") or host.endswith(domain)


def score_email(email: str, website: str | None = None) -> int:
    email = email.lower().strip()
    if not is_valid_email(email):
        return -100
    score = 10
    if email_matches_website(email, website):
        score += 50
    if any(email.startswith(prefix) for prefix in BUSINESS_EMAIL_LOCAL_PREFIXES):
        score += 25
    domain = _email_domain(email)
    if domain in FREE_EMAIL_DOMAINS:
        score += 5
    else:
        score += 15
    return score


def pick_best_email(emails: list[str], website: str | None = None) -> str | None:
    unique: list[str] = []
    seen: set[str] = set()
    for email in emails:
        key = email.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(key)

    if not unique:
        return None

    ranked = sorted(unique, key=lambda e: score_email(e, website), reverse=True)
    best = ranked[0]
    return best if score_email(best, website) > 0 else None


def extract_emails_from_text(text: str, website: str | None = None) -> list[str]:
    found: list[str] = []
    for match in EMAIL_PATTERN.findall(text):
        email = match.lower().strip()
        if is_valid_email(email) and email not in found:
            found.append(email)
    for match in OBFUSCATED_EMAIL_PATTERN.finditer(text):
        email = f"{match.group(1)}@{match.group(2)}".lower().strip()
        if is_valid_email(email) and email not in found:
            found.append(email)
    found.sort(key=lambda e: score_email(e, website), reverse=True)
    return found


def extract_instagram_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in INSTAGRAM_PATTERN.findall(text):
        clean = match.rstrip("/).,;")
        if clean not in urls:
            urls.append(clean)
    return urls


def extract_facebook_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in FACEBOOK_PATTERN.findall(text):
        clean = match.rstrip("/).,;")
        if "/sharer" in clean.lower() or "/share" in clean.lower():
            continue
        if clean not in urls:
            urls.append(clean)
    return urls


def extract_linkedin_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in LINKEDIN_PATTERN.findall(text):
        clean = match.rstrip("/).,;")
        if clean not in urls:
            urls.append(clean)
    return urls


def infer_country_from_location(location: str | None) -> str | None:
    if not location:
        return None
    parts = [p.strip() for p in location.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[-1]
    if parts:
        city_key = parts[0].lower()
        if city_key in CITY_COUNTRY_HINTS:
            return CITY_COUNTRY_HINTS[city_key]
        for city, country in CITY_COUNTRY_HINTS.items():
            if city in city_key:
                return country
    return parts[0] if parts else None


def _infer_country_from_digits(digits: str) -> str | None:
    inferred = phone_lib.infer_country_from_digits(digits)
    if inferred:
        return inferred
    if digits.startswith("923") and len(digits) == 12:
        return "Pakistan"
    if digits.startswith("9715") and len(digits) in (11, 12):
        return "UAE"
    if digits.startswith("9665") and len(digits) == 12:
        return "Saudi Arabia"
    if len(digits) == 11 and digits.startswith("03"):
        return "Pakistan"
    if len(digits) == 10 and digits.startswith("3"):
        return "Pakistan"
    if len(digits) == 9 and digits.startswith("5"):
        return "UAE"
    return None


def _effective_country(country: str | None, digits: str) -> str | None:
    if _country_code(country):
        return country
    return _infer_country_from_digits(digits) or country


def _country_code(country: str | None) -> str | None:
    if not country:
        return None
    key = country.strip().lower()
    if key in COUNTRY_PHONE_CODES:
        return COUNTRY_PHONE_CODES[key]
    for name, code in COUNTRY_PHONE_CODES.items():
        if name in key or key in name:
            return code
    return None


def _digits_only(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def extract_phone_from_whatsapp_href(href: str) -> str | None:
    """Extract raw digits from wa.me / WhatsApp API links."""
    if not href:
        return None
    href = href.strip()
    patterns = (
        WA_ME_PATTERN,
        WHATSAPP_SEND_PATTERN,
        WHATSAPP_PHONE_PARAM_PATTERN,
        WEB_WHATSAPP_PATTERN,
    )
    for pattern in patterns:
        match = pattern.search(href)
        if match:
            digits = match.group(1)
            if 10 <= len(digits) <= 15:
                return digits
    return None


def _effective_country_for_phone(phone: str | None, country: str | None) -> str | None:
    digits = _digits_only(phone or "")
    if len(digits) >= 10:
        inferred = phone_lib.infer_country_from_digits(digits)
        if inferred:
            return inferred
    return country


def _looks_like_year_or_date(raw: str) -> bool:
    digits = _digits_only(raw)
    if re.search(r"20[12]\d", raw):
        return True
    if len(digits) == 4 and digits.startswith("20"):
        return True
    if len(digits) == 8 and digits[:4].startswith("20"):
        return True
    return False


def _matches_known_whatsapp_format(digits: str) -> bool:
    if _is_fake_phone_digits(digits):
        return False
    for pattern, _country in WHATSAPP_DIGIT_PATTERNS:
        if pattern.match(digits):
            return True
    return False


def _infer_country_from_valid_digits(digits: str) -> str | None:
    for pattern, country in WHATSAPP_DIGIT_PATTERNS:
        if pattern.match(digits):
            return country
    return None


def _is_fake_phone_digits(digits: str) -> bool:
    if len(digits) < 10:
        return True
    if len(digits) > 15:
        return True
    if len(set(digits)) <= 2:
        return True
    if digits in {"1234567890", "0123456789", "123456789", "0000000000", "12345678901"}:
        return True
    # CSS/screen dimensions, timestamps
    if digits.startswith("20") and len(digits) == 10:
        return True
    if re.match(r"^20[12]\d", digits) and len(digits) <= 12:
        return True
    # Pakistan landline after partial normalize (92 + landline)
    if digits.startswith("92") and len(digits) == 12 and digits[2] in "2456":
        return True
    return False


def _validate_mobile_for_country(digits: str, country: str | None) -> bool:
    if _matches_known_whatsapp_format(digits):
        return True

    if _is_fake_phone_digits(digits):
        return False

    # libphonenumber handles all countries (not just PK/UAE/UK)
    e164 = phone_lib.normalize_whatsapp_e164(f"+{digits}", country)
    if e164:
        return True

    code = _country_code(country)
    if code == "92":
        return len(digits) == 12 and digits.startswith("923")
    if code == "971":
        return len(digits) == 12 and digits.startswith("9715")
    if code == "966":
        return len(digits) == 12 and digits.startswith("9665")
    if code == "91":
        return len(digits) == 12 and digits.startswith("91") and digits[2] in "6789"
    if code == "44":
        return len(digits) == 12 and digits.startswith("447")
    if code == "1":
        return len(digits) == 11 and digits.startswith("1") and digits[1] in "23456789"

    return False


def normalize_whatsapp_phone(
    phone: str | None,
    country: str | None = None,
    *,
    from_whatsapp_link: bool = False,
) -> str | None:
    if not phone or not phone.strip():
        return None

    raw = phone.strip()
    wa_digits = extract_phone_from_whatsapp_href(raw)
    is_wa_source = from_whatsapp_link or bool(wa_digits)

    if wa_digits:
        country = _effective_country_for_phone(wa_digits, country)

    # Google libphonenumber — primary validator
    e164 = phone_lib.normalize_whatsapp_e164(
        raw if not wa_digits else f"+{wa_digits}",
        country,
        trust_whatsapp_link=is_wa_source,
    )
    if e164:
        return e164.lstrip("+")

    digits = wa_digits or _digits_only(raw)
    if digits.startswith("00"):
        digits = digits[2:]
    if _is_fake_phone_digits(digits):
        return None

    country = _effective_country_for_phone(digits, country)
    country_code = _country_code(country)

    if country_code:
        if digits.startswith("0") and len(digits) >= 10:
            digits = country_code + digits[1:]
        elif digits.startswith(country_code):
            pass
        elif country_code == "92" and len(digits) == 10 and digits.startswith("3"):
            digits = country_code + digits
        elif country_code == "92" and len(digits) == 11 and digits.startswith("03"):
            digits = country_code + digits[2:]
        elif country_code == "971" and len(digits) == 9 and digits.startswith("5"):
            digits = country_code + digits
        elif country_code == "971" and len(digits) == 10 and digits.startswith("05"):
            digits = country_code + digits[1:]
        elif country_code == "44" and len(digits) == 11 and digits.startswith("07"):
            digits = country_code + digits[1:]
        elif country_code == "44" and len(digits) == 10 and digits.startswith("7"):
            digits = country_code + digits
        elif country_code == "49" and len(digits) >= 10 and digits.startswith("1"):
            digits = country_code + digits
        elif country_code == "33" and len(digits) == 9 and digits[0] in "67":
            digits = country_code + digits
        elif country_code == "31" and len(digits) == 9 and digits.startswith("6"):
            digits = country_code + digits
        elif country_code == "34" and len(digits) == 9 and digits[0] in "67":
            digits = country_code + digits
        elif country_code == "39" and len(digits) >= 9 and digits.startswith("3"):
            digits = country_code + digits
        elif country_code == "353" and len(digits) == 9 and digits.startswith("8"):
            digits = country_code + digits
        elif len(digits) == 10 and country_code == "1":
            digits = country_code + digits

    if not _validate_mobile_for_country(digits, country):
        return None

    e164 = phone_lib.normalize_whatsapp_e164(
        f"+{digits}",
        country,
        trust_whatsapp_link=is_wa_source,
    )
    if e164:
        return e164.lstrip("+")

    return None


def _add_phone_candidate(
    candidates: list[str], raw: str, country: str | None, *, from_whatsapp: bool = False
) -> None:
    if _looks_like_year_or_date(raw):
        return
    if from_whatsapp:
        wa_digits = extract_phone_from_whatsapp_href(raw) or _digits_only(raw)
        effective_country = _effective_country_for_phone(wa_digits, country)
        normalized = normalize_whatsapp_phone(
            wa_digits, effective_country, from_whatsapp_link=True
        )
    else:
        effective_country = _effective_country_for_phone(raw, country)
        normalized = normalize_whatsapp_phone(raw, effective_country)
    if normalized:
        formatted = f"+{normalized}"
        if formatted not in candidates:
            candidates.append(formatted)


def _extract_libphonenumber_matches(text: str, country: str | None, candidates: list[str]) -> None:
    for e164 in phone_lib.find_numbers_in_text_multi_region(text, country):
        _add_phone_candidate(candidates, e164, country)


def _countries_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    al, bl = a.strip().lower(), b.strip().lower()
    if al == bl or al in bl or bl in al:
        return True
    return _country_code(a) == _country_code(b) and _country_code(a) is not None


def _has_explicit_intl_prefix(digits: str) -> bool:
    """True when digits clearly include a country calling code (not a local 07xx guess)."""
    prefixes = (
        "923", "971", "966", "447", "491", "336", "337", "316", "353", "346", "347", "393", "91", "1"
    )
    return any(digits.startswith(p) for p in prefixes)


def score_phone(phone: str, country: str | None = None) -> int:
    normalized = normalize_whatsapp_phone(phone, country)
    if not normalized:
        return -1
    score = 10
    lower = phone.lower()
    if "wa.me" in lower or "whatsapp" in lower or "api.whatsapp" in lower:
        score += 50
    if "tel:" in lower:
        score += 10
    if _matches_known_whatsapp_format(normalized):
        score += 20

    inferred = phone_lib.infer_country_from_digits(normalized) or _infer_country_from_valid_digits(
        normalized
    )
    if country and inferred:
        if _countries_match(inferred, country):
            score += 80
        elif not _has_explicit_intl_prefix(normalized):
            score -= 70
    return score


def _extract_country_mobile_patterns(text: str, country: str | None, candidates: list[str]) -> None:
    if not country:
        return
    code = _country_code(country)
    if code == "92":
        for match in PK_MOBILE_TEXT_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)
    elif code == "971":
        for match in UAE_MOBILE_TEXT_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)
    elif code == "44" or "kingdom" in country.lower():
        for match in UK_MOBILE_TEXT_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)
    elif code == "49" or "germany" in country.lower():
        for match in EU_DE_MOBILE_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)
    elif code == "33" or "france" in country.lower():
        for match in EU_FR_MOBILE_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)
    elif code == "31" or "netherlands" in country.lower():
        for match in EU_NL_MOBILE_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)
    elif code == "353" or "ireland" in country.lower():
        for match in EU_IE_MOBILE_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)
    elif code == "34" or "spain" in country.lower():
        for match in EU_ES_MOBILE_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)
    elif code == "39" or "italy" in country.lower():
        for match in EU_IT_MOBILE_PATTERN.finditer(text):
            _add_phone_candidate(candidates, match.group(0), country)


def _extract_whatsapp_urls_from_text(text: str, country: str | None, candidates: list[str]) -> None:
    for match in WA_ME_PATTERN.findall(text):
        _add_phone_candidate(candidates, match, country, from_whatsapp=True)
    for match in WHATSAPP_SEND_PATTERN.findall(text):
        _add_phone_candidate(candidates, match, country, from_whatsapp=True)
    for match in WHATSAPP_PHONE_PARAM_PATTERN.findall(text):
        _add_phone_candidate(candidates, match, country, from_whatsapp=True)
    for match in WEB_WHATSAPP_PATTERN.findall(text):
        _add_phone_candidate(candidates, match, country, from_whatsapp=True)


def extract_phones_from_snippet(text: str, country: str | None = None) -> list[str]:
    """High-confidence phone extraction for search snippets."""
    from app.utils.phone_confidence import PhoneHit, aggregate_phone_hits

    if not text:
        return []

    hits: list[PhoneHit] = []
    for match in WA_ME_PATTERN.findall(text):
        h = PhoneHit(raw=match, source="search_snippet", country=country, from_whatsapp=True)
        if h.resolved_e164():
            hits.append(h)
    for pattern in (WHATSAPP_SEND_PATTERN, WHATSAPP_PHONE_PARAM_PATTERN, WEB_WHATSAPP_PATTERN):
        for match in pattern.findall(text):
            h = PhoneHit(raw=match, source="search_snippet", country=country, from_whatsapp=True)
            if h.resolved_e164():
                hits.append(h)

    for match in WHATSAPP_LABEL_PATTERN.findall(text):
        h = PhoneHit(raw=match, source="whatsapp_label", country=country)
        if h.resolved_e164():
            hits.append(h)

    for match in TEL_HREF_PATTERN.findall(text):
        h = PhoneHit(raw=match, source="tel_link", country=country)
        if h.resolved_e164():
            hits.append(h)

    verified = aggregate_phone_hits(hits, country)
    return [verified] if verified else []


def extract_phones_from_text(text: str, country: str | None = None) -> list[str]:
    if not text:
        return []

    if "<" in text and ("href=" in text.lower() or "<html" in text.lower() or "<body" in text.lower()):
        from app.utils.phone_extract import extract_phones_from_html

        return extract_phones_from_html(text, country)

    return extract_phones_from_snippet(text, country)


def format_whatsapp_display(
    phone: str | None, country: str | None = None, *, from_whatsapp_link: bool = False
) -> str | None:
    """Return E.164 +XXXXXXXXXXX for storage/display."""
    if not phone:
        return None
    effective_country = _effective_country_for_phone(phone, country)
    wa_digits = extract_phone_from_whatsapp_href(str(phone))
    is_wa = from_whatsapp_link or bool(wa_digits)
    e164 = phone_lib.normalize_whatsapp_e164(
        phone if not wa_digits else f"+{wa_digits}",
        effective_country,
        trust_whatsapp_link=is_wa,
    )
    if e164:
        return e164
    normalized = normalize_whatsapp_phone(phone, effective_country, from_whatsapp_link=is_wa)
    return f"+{normalized}" if normalized else None


def format_contact_phone(
    phone: str | None, country: str | None = None, *, from_whatsapp_link: bool = False
) -> str | None:
    """Return E.164 for lead storage — keeps mobile and landline business numbers."""
    if not phone:
        return None
    effective_country = _effective_country_for_phone(phone, country)
    wa_digits = extract_phone_from_whatsapp_href(str(phone))
    is_wa = from_whatsapp_link or bool(wa_digits)
    raw = phone if not wa_digits else f"+{wa_digits}"
    e164 = phone_lib.normalize_whatsapp_e164(
        raw,
        effective_country,
        trust_whatsapp_link=is_wa,
    )
    if e164:
        return e164
    return phone_lib.normalize_contact_e164(raw, effective_country)


def pick_best_phone(
    phones: list[str], country: str | None = None, *, min_score: int = 75
) -> str | None:
    if not phones:
        return None
    ranked = sorted(phones, key=lambda p: score_phone(p, country), reverse=True)
    if score_phone(ranked[0], country) < min_score:
        return None

    country_hints: list[str | None] = []
    if country:
        country_hints.append(country)
    for phone in ranked:
        inferred = _effective_country_for_phone(phone, country)
        if inferred and inferred not in country_hints:
            country_hints.insert(0, inferred)

    for phone in ranked:
        for hint in country_hints or [country]:
            normalized = normalize_whatsapp_phone(phone, hint)
            if normalized:
                return f"+{normalized}"
    return None


def is_whatsapp_ready(phone: str | None, country: str | None = None) -> bool:
    effective_country = _effective_country_for_phone(phone, country)
    return phone_lib.is_strict_whatsapp_mobile(phone, effective_country)


def build_whatsapp_link(phone: str, message: str = "") -> str:
    from urllib.parse import quote

    digits = _digits_only(phone)
    base = f"https://wa.me/{digits}"
    if message.strip():
        return f"{base}?text={quote(message)}"
    return base
