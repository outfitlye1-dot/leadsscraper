"""Map scrape location strings to Meta Ad Library ISO country codes."""

from __future__ import annotations

from app.utils.scrape_defaults import EUROPE_CITY_COUNTRY, LOCATION_ALIASES
from app.utils.scrape_sources import parse_location_parts

COUNTRY_NAME_TO_ISO: dict[str, str] = {
    "united kingdom": "GB",
    "uk": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "germany": "DE",
    "netherlands": "NL",
    "france": "FR",
    "spain": "ES",
    "ireland": "IE",
    "italy": "IT",
    "belgium": "BE",
    "austria": "AT",
    "poland": "PL",
    "sweden": "SE",
    "portugal": "PT",
    "switzerland": "CH",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "czech republic": "CZ",
    "romania": "RO",
    "greece": "GR",
    "united states": "US",
    "usa": "US",
    "canada": "CA",
    "australia": "AU",
    "pakistan": "PK",
    "uae": "AE",
    "united arab emirates": "AE",
    "india": "IN",
    "turkey": "TR",
    "brazil": "BR",
    "mexico": "MX",
    "europe": "GB",
    "european": "GB",
}

CITY_TO_ISO: dict[str, str] = {
    city: COUNTRY_NAME_TO_ISO.get(country.lower(), "GB")
    for city, country in EUROPE_CITY_COUNTRY.items()
}
CITY_TO_ISO.update(
    {
        "karachi": "PK",
        "lahore": "PK",
        "islamabad": "PK",
        "dubai": "AE",
        "new york": "US",
        "los angeles": "US",
        "toronto": "CA",
        "sydney": "AU",
    }
)


def location_to_iso_country(location: str, default: str = "GB") -> str:
    loc = (location or "").strip()
    if not loc:
        return default

    lowered = loc.lower()
    if lowered in LOCATION_ALIASES:
        loc = LOCATION_ALIASES[lowered]
        lowered = loc.lower()

    if lowered in COUNTRY_NAME_TO_ISO:
        return COUNTRY_NAME_TO_ISO[lowered]

    city, country = parse_location_parts(loc)
    if country:
        country_key = country.lower()
        if country_key in COUNTRY_NAME_TO_ISO:
            return COUNTRY_NAME_TO_ISO[country_key]

    if city:
        city_key = city.lower()
        if city_key in CITY_TO_ISO:
            return CITY_TO_ISO[city_key]

    for token in lowered.replace(",", " ").split():
        if token in COUNTRY_NAME_TO_ISO:
            return COUNTRY_NAME_TO_ISO[token]
        if token in CITY_TO_ISO:
            return CITY_TO_ISO[token]

    return default


def build_ad_library_url(keyword: str, country_iso: str) -> str:
    from urllib.parse import quote_plus

    q = quote_plus(keyword.strip())
    country = (country_iso or "GB").upper()
    return (
        "https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country={country}"
        f"&q={q}&search_type=keyword_unordered&media_type=all"
    )
