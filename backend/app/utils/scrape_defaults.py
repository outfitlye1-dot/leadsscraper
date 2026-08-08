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

# Country → major cities for multi-agent auto scrape
COUNTRY_CITIES: dict[str, list[str]] = {
    "United Kingdom": [
        "London",
        "Manchester",
        "Birmingham",
        "Leeds",
        "Glasgow",
        "Liverpool",
        "Bristol",
        "Edinburgh",
        "Sheffield",
        "Newcastle",
        "Nottingham",
        "Cardiff",
    ],
    "Germany": [
        "Berlin",
        "Munich",
        "Hamburg",
        "Frankfurt",
        "Cologne",
        "Stuttgart",
        "Düsseldorf",
        "Dortmund",
        "Leipzig",
        "Dresden",
    ],
    "France": [
        "Paris",
        "Lyon",
        "Marseille",
        "Toulouse",
        "Nice",
        "Nantes",
        "Strasbourg",
        "Bordeaux",
        "Lille",
        "Rennes",
    ],
    "Netherlands": [
        "Amsterdam",
        "Rotterdam",
        "The Hague",
        "Utrecht",
        "Eindhoven",
        "Groningen",
        "Tilburg",
        "Haarlem",
    ],
    "Spain": [
        "Madrid",
        "Barcelona",
        "Valencia",
        "Seville",
        "Zaragoza",
        "Malaga",
        "Bilbao",
        "Murcia",
    ],
    "Italy": [
        "Milan",
        "Rome",
        "Naples",
        "Turin",
        "Florence",
        "Bologna",
        "Genoa",
        "Palermo",
    ],
    "Ireland": ["Dublin", "Cork", "Galway", "Limerick", "Waterford"],
    "Belgium": ["Brussels", "Antwerp", "Ghent", "Bruges", "Liege"],
    "Austria": ["Vienna", "Graz", "Linz", "Salzburg", "Innsbruck"],
    "Poland": ["Warsaw", "Krakow", "Wroclaw", "Gdansk", "Poznan", "Lodz"],
    "Portugal": ["Lisbon", "Porto", "Braga", "Coimbra", "Faro"],
    "Sweden": ["Stockholm", "Gothenburg", "Malmo", "Uppsala"],
    "Pakistan": [
        "Karachi",
        "Lahore",
        "Islamabad",
        "Rawalpindi",
        "Faisalabad",
        "Multan",
        "Peshawar",
        "Quetta",
    ],
    "United Arab Emirates": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman"],
    "United States": [
        "New York",
        "Los Angeles",
        "Chicago",
        "Houston",
        "Phoenix",
        "Miami",
        "Dallas",
        "Atlanta",
        "Seattle",
        "Boston",
    ],
}

# Aliases → canonical country key in COUNTRY_CITIES
COUNTRY_ALIASES: dict[str, str] = {
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "england": "United Kingdom",
    "britain": "United Kingdom",
    "gb": "United Kingdom",
    "germany": "Germany",
    "de": "Germany",
    "france": "France",
    "fr": "France",
    "netherlands": "Netherlands",
    "holland": "Netherlands",
    "nl": "Netherlands",
    "spain": "Spain",
    "es": "Spain",
    "italy": "Italy",
    "it": "Italy",
    "ireland": "Ireland",
    "ie": "Ireland",
    "belgium": "Belgium",
    "be": "Belgium",
    "austria": "Austria",
    "at": "Austria",
    "poland": "Poland",
    "pl": "Poland",
    "portugal": "Portugal",
    "pt": "Portugal",
    "sweden": "Sweden",
    "se": "Sweden",
    "pakistan": "Pakistan",
    "pk": "Pakistan",
    "uae": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
    "dubai": "United Arab Emirates",
    "usa": "United States",
    "us": "United States",
    "united states": "United States",
    "america": "United States",
}


def normalize_country_name(country: str | None) -> str | None:
    if not country or not str(country).strip():
        return None
    key = str(country).strip()
    if key in COUNTRY_CITIES:
        return key
    return COUNTRY_ALIASES.get(key.lower())


def cities_for_country(country: str | None) -> list[str]:
    """Return 'City, Country' locations for multi-agent country scrape."""
    canonical = normalize_country_name(country)
    if not canonical:
        return []
    cities = COUNTRY_CITIES.get(canonical) or []
    return [f"{city}, {canonical}" for city in cities]


def list_scrape_countries() -> list[str]:
    return sorted(COUNTRY_CITIES.keys())


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
