"""Default scrape targeting — Europe-first; other regions only when user specifies."""

from __future__ import annotations

DEFAULT_SCRAPE_LOCATION = "London, United Kingdom"

EUROPE_LOCATION_SUGGESTIONS = [
    "London, United Kingdom",
    "Berlin, Germany",
    "Amsterdam, Netherlands",
    "Paris, France",
    "Madrid, Spain",
    "Dublin, Ireland",
    "Milan, Italy",
    "Brussels, Belgium",
    "Vienna, Austria",
    "Warsaw, Poland",
    "Stockholm, Sweden",
    "Lisbon, Portugal",
]

EUROPE_LOCATION_HINTS = (
    "united kingdom",
    "uk",
    "london",
    "england",
    "scotland",
    "wales",
    "germany",
    "berlin",
    "munich",
    "frankfurt",
    "netherlands",
    "amsterdam",
    "rotterdam",
    "france",
    "paris",
    "lyon",
    "spain",
    "madrid",
    "barcelona",
    "ireland",
    "dublin",
    "europe",
    "european",
    "italy",
    "rome",
    "milan",
    "portugal",
    "lisbon",
    "belgium",
    "brussels",
    "sweden",
    "stockholm",
    "poland",
    "warsaw",
    "austria",
    "vienna",
    "switzerland",
    "zurich",
    "geneva",
    "denmark",
    "copenhagen",
    "norway",
    "oslo",
    "finland",
    "helsinki",
    "czech",
    "prague",
    "romania",
    "bucharest",
    "greece",
    "athens",
)

PAKISTAN_LOCATION_HINTS = (
    "pakistan",
    "karachi",
    "lahore",
    "islamabad",
    "rawalpindi",
    "faisalabad",
)

# Single-word / shorthand → "City, Country" for Apify & forms
LOCATION_ALIASES: dict[str, str] = {
    "uk": "London, United Kingdom",
    "united kingdom": "London, United Kingdom",
    "england": "London, United Kingdom",
    "london": "London, United Kingdom",
    "germany": "Berlin, Germany",
    "berlin": "Berlin, Germany",
    "netherlands": "Amsterdam, Netherlands",
    "amsterdam": "Amsterdam, Netherlands",
    "france": "Paris, France",
    "paris": "Paris, France",
    "spain": "Madrid, Spain",
    "madrid": "Madrid, Spain",
    "ireland": "Dublin, Ireland",
    "dublin": "Dublin, Ireland",
    "italy": "Milan, Italy",
    "milan": "Milan, Italy",
    "belgium": "Brussels, Belgium",
    "brussels": "Brussels, Belgium",
    "austria": "Vienna, Austria",
    "vienna": "Vienna, Austria",
    "poland": "Warsaw, Poland",
    "warsaw": "Warsaw, Poland",
    "sweden": "Stockholm, Sweden",
    "stockholm": "Stockholm, Sweden",
    "portugal": "Lisbon, Portugal",
    "lisbon": "Lisbon, Portugal",
    "europe": DEFAULT_SCRAPE_LOCATION,
    "european": DEFAULT_SCRAPE_LOCATION,
    "global": DEFAULT_SCRAPE_LOCATION,
    "pakistan": "Karachi, Pakistan",
    "lahore": "Lahore, Pakistan",
    "karachi": "Karachi, Pakistan",
    "islamabad": "Islamabad, Pakistan",
    "dubai": "Dubai, UAE",
    "uae": "Dubai, UAE",
    "usa": "New York, United States",
    "united states": "New York, United States",
}

EUROPE_CITY_COUNTRY: dict[str, str] = {
    "london": "United Kingdom",
    "manchester": "United Kingdom",
    "birmingham": "United Kingdom",
    "berlin": "Germany",
    "munich": "Germany",
    "hamburg": "Germany",
    "frankfurt": "Germany",
    "amsterdam": "Netherlands",
    "rotterdam": "Netherlands",
    "paris": "France",
    "lyon": "France",
    "marseille": "France",
    "madrid": "Spain",
    "barcelona": "Spain",
    "dublin": "Ireland",
    "milan": "Italy",
    "rome": "Italy",
    "brussels": "Belgium",
    "vienna": "Austria",
    "zurich": "Switzerland",
    "geneva": "Switzerland",
    "stockholm": "Sweden",
    "oslo": "Norway",
    "copenhagen": "Denmark",
    "helsinki": "Finland",
    "warsaw": "Poland",
    "prague": "Czech Republic",
    "lisbon": "Portugal",
    "bucharest": "Romania",
    "athens": "Greece",
}


def is_europe_target(location: str | None) -> bool:
    if not location:
        return True
    lower = location.lower()
    if any(h in lower for h in PAKISTAN_LOCATION_HINTS):
        return False
    if any(h in lower for h in EUROPE_LOCATION_HINTS):
        return True
    if "," in location:
        country = location.split(",")[-1].strip().lower()
        return country in {
            "united kingdom",
            "uk",
            "germany",
            "france",
            "netherlands",
            "spain",
            "ireland",
            "italy",
            "belgium",
            "austria",
            "switzerland",
            "sweden",
            "norway",
            "denmark",
            "finland",
            "poland",
            "portugal",
            "czech republic",
            "romania",
            "greece",
        }
    return False


def resolve_scrape_location(location: str | None) -> str:
    """Normalize location; default to Europe (London, UK) when empty or 'Global'."""
    if not location or not str(location).strip():
        return DEFAULT_SCRAPE_LOCATION
    text = str(location).strip()
    lower = text.lower()
    if lower in ("global", "worldwide", "international", "anywhere"):
        return DEFAULT_SCRAPE_LOCATION
    if "," in text:
        return text
    if lower in LOCATION_ALIASES:
        return LOCATION_ALIASES[lower]
    return text


def normalize_location_alias(location: str) -> str:
    """Expand shorthand city/country names for Google Maps."""
    return resolve_scrape_location(location)
