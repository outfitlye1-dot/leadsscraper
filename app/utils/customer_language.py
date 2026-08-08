"""Map customer country → language instructions for Brain outreach copy."""

from __future__ import annotations

# Country name / alias (lowercase) → (language label, script notes for the model)
_COUNTRY_LANGUAGE: dict[str, tuple[str, str]] = {
    # South Asia
    "pakistan": ("Urdu (Roman Urdu)", "WhatsApp style Roman Urdu — natural local chat, not heavy formal Urdu script unless the customer used Nastaliq"),
    "pk": ("Urdu (Roman Urdu)", "WhatsApp style Roman Urdu"),
    "india": ("Hindi (Roman Hindi) or simple English", "Prefer Roman Hindi for local SMBs; mix English business words if natural"),
    "in": ("Hindi (Roman Hindi) or simple English", "Prefer Roman Hindi for local SMBs"),
    "bangladesh": ("Bangla (Roman Bangla) or simple English", "Natural local chat tone"),
    "bd": ("Bangla (Roman Bangla) or simple English", "Natural local chat tone"),
    # Middle East / Gulf
    "united arab emirates": ("Arabic", "Modern standard / Gulf WhatsApp Arabic; keep short"),
    "uae": ("Arabic", "Gulf WhatsApp Arabic"),
    "saudi arabia": ("Arabic", "Saudi WhatsApp Arabic"),
    "ksa": ("Arabic", "Saudi WhatsApp Arabic"),
    "qatar": ("Arabic", "Gulf WhatsApp Arabic"),
    "kuwait": ("Arabic", "Gulf WhatsApp Arabic"),
    "bahrain": ("Arabic", "Gulf WhatsApp Arabic"),
    "oman": ("Arabic", "Gulf WhatsApp Arabic"),
    "egypt": ("Arabic", "Egyptian colloquial WhatsApp Arabic is fine"),
    "jordan": ("Arabic", "Levantine WhatsApp Arabic is fine"),
    "lebanon": ("Arabic", "Levantine WhatsApp Arabic is fine"),
    "iraq": ("Arabic", "Iraqi WhatsApp Arabic is fine"),
    "morocco": ("Arabic or French", "Match local business chat; French OK for Casablanca/Rabat SMBs"),
    "algeria": ("Arabic or French", "French OK for business WhatsApp"),
    "tunisia": ("Arabic or French", "French OK for business WhatsApp"),
    # Europe
    "united kingdom": ("English (UK)", "British English spelling and tone"),
    "uk": ("English (UK)", "British English"),
    "england": ("English (UK)", "British English"),
    "scotland": ("English (UK)", "British English"),
    "wales": ("English (UK)", "British English"),
    "ireland": ("English", "Natural Irish/UK business English"),
    "germany": ("German", "Clear informal Sie/du appropriate for SMB WhatsApp — prefer polite Sie"),
    "de": ("German", "Polite business German"),
    "france": ("French", "Natural French for SMB outreach"),
    "fr": ("French", "Natural French"),
    "spain": ("Spanish", "Neutral Latin American / European Spanish — clear and short"),
    "es": ("Spanish", "Clear Spanish"),
    "italy": ("Italian", "Natural Italian"),
    "it": ("Italian", "Natural Italian"),
    "portugal": ("Portuguese (Portugal)", "European Portuguese"),
    "netherlands": ("Dutch", "Natural Dutch; English OK only if customer wrote English"),
    "belgium": ("Dutch or French", "Match city/region if known; otherwise French or Dutch simply"),
    "poland": ("Polish", "Natural Polish"),
    "sweden": ("Swedish", "Natural Swedish"),
    "norway": ("Norwegian", "Natural Norwegian"),
    "denmark": ("Danish", "Natural Danish"),
    "austria": ("German", "Austrian/German business tone"),
    "switzerland": ("German or French", "Match region if known; otherwise German"),
    "greece": ("Greek", "Natural Greek"),
    "turkey": ("Turkish", "Natural Turkish"),
    "türkiye": ("Turkish", "Natural Turkish"),
    # Americas
    "united states": ("English (US)", "American English"),
    "usa": ("English (US)", "American English"),
    "us": ("English (US)", "American English"),
    "canada": ("English", "Canadian English; French only if Quebec/French context is clear"),
    "mexico": ("Spanish (Mexico)", "Mexican Spanish"),
    "brazil": ("Portuguese (Brazil)", "Brazilian Portuguese"),
    "argentina": ("Spanish (Argentina)", "Rioplatense Spanish OK"),
    "colombia": ("Spanish", "Latin American Spanish"),
    "chile": ("Spanish", "Latin American Spanish"),
    # Africa / Asia-Pacific
    "nigeria": ("English (Nigeria)", "Natural Nigerian business English"),
    "kenya": ("English", "Natural East African business English"),
    "south africa": ("English", "South African English"),
    "china": ("Chinese (Simplified)", "简体中文 — short WeChat/WhatsApp style"),
    "japan": ("Japanese", "Polite business Japanese"),
    "south korea": ("Korean", "Polite business Korean"),
    "indonesia": ("Indonesian", "Bahasa Indonesia"),
    "malaysia": ("Malay or English", "Match local business chat"),
    "philippines": ("English or Tagalog", "English default; Tagalog if natural"),
    "australia": ("English (Australia)", "Australian English"),
    "new zealand": ("English", "NZ English"),
}


def resolve_customer_language(country: str | None, city: str | None = None) -> tuple[str, str]:
    """Return (language_label, style_note) for a lead's country."""
    raw = (country or "").strip()
    if not raw and city:
        # e.g. "Lahore, Pakistan" stuck in city, or city-only scrapes
        raw = city.strip()
    if not raw:
        return ("English", "Clear simple English")

    lower = raw.lower()
    # Try full string, then last comma part (City, Country)
    candidates = [lower]
    if "," in lower:
        candidates.append(lower.split(",")[-1].strip())
        candidates.append(lower.split(",")[0].strip())

    for key in candidates:
        if key in _COUNTRY_LANGUAGE:
            return _COUNTRY_LANGUAGE[key]
        for alias, value in _COUNTRY_LANGUAGE.items():
            if alias in key or key in alias:
                return value

    return ("English", f"Clear simple English suited to customers in {raw}")


def language_rules_for_country(
    country: str | None,
    city: str | None = None,
    *,
    channel: str = "whatsapp",
) -> str:
    """Prompt block: write in the customer's local language."""
    language, style = resolve_customer_language(country, city)
    place = ", ".join(p for p in [city, country] if (p or "").strip()) or "unknown location"
    channel_label = "WhatsApp" if channel == "whatsapp" else channel

    greeting = "Use a respectful local greeting (e.g. Assalam o Alaikum / Hi sir for Pakistan; Hi sir for English)."
    if language.startswith("Arabic"):
        greeting = 'Start with "السلام عليكم" or a short polite Arabic greeting — not English "Hi sir,".'
    elif language.startswith("Urdu"):
        greeting = 'Start with "Assalam o Alaikum," or "Hi sir," — respectful Pakistani WhatsApp tone.'
    elif language.startswith("Hindi"):
        greeting = 'Start with "Namaste," or "Hi sir," — respectful local tone.'
    elif language.startswith("German"):
        greeting = 'Start with "Guten Tag," or "Hallo," — polite; avoid English "Hi sir,".'
    elif language.startswith("French"):
        greeting = 'Start with "Bonjour," — polite; avoid English "Hi sir,".'
    elif language.startswith("Spanish"):
        greeting = 'Start with "Hola," — polite; avoid English "Hi sir,".'
    elif language.startswith("Turkish"):
        greeting = 'Start with "Merhaba," — polite; avoid English "Hi sir,".'
    elif language.startswith("Chinese"):
        greeting = "Start with a short polite Chinese greeting (您好)."
    elif language.startswith("Japanese"):
        greeting = "Start with a polite Japanese greeting (こんにちは / 失礼します)."
    elif "Portuguese" in language:
        greeting = 'Start with "Olá," — polite; avoid English "Hi sir,".'
    elif language.startswith("Dutch"):
        greeting = 'Start with "Goedendag," or "Hallo," — polite.'
    elif language.startswith("Polish"):
        greeting = 'Start with "Dzień dobry," — polite.'
    elif language.startswith("Italian"):
        greeting = 'Start with "Buongiorno," or "Ciao," — polite.'

    return f"""LANGUAGE (critical — customer location: {place}):
- Write the ENTIRE {channel_label} message in: {language}
- Style: {style}
- {greeting}
- If the customer already wrote in another language in this thread, MATCH their language instead.
- Do NOT invent English then translate poorly — write naturally in the target language.
- Keep numbers, brand names, and URLs as-is.
"""
