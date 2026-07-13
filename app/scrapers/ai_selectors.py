"""AI-powered CSS selector discovery, validation, and repair."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_selector_cache: dict[str, dict[str, list[str]]] = {}
_cache_lock = threading.Lock()

DEFAULT_CONTACT_SELECTORS = [
    'a[href^="mailto:"]',
    'a[href^="tel:"]',
    'a[href*="wa.me"]',
    'a[href*="whatsapp.com"]',
    '[itemtype*="LocalBusiness"]',
    '[itemtype*="Organization"]',
    "address",
    ".contact",
    "#contact",
]

DEFAULT_FIELD_SELECTORS = {
    "email": ['a[href^="mailto:"]', '[itemprop="email"]'],
    "phone": ['a[href^="tel:"]', '[itemprop="telephone"]'],
    "company": ["h1", '[itemprop="name"]', "meta[property='og:site_name']"],
    "address": ["address", '[itemprop="address"]'],
}


@dataclass
class SelectorSchema:
    host: str
    selectors: dict[str, list[str]] = field(default_factory=dict)
    fallbacks: list[str] = field(default_factory=list)

    def all_selectors(self) -> list[str]:
        out: list[str] = []
        for group in self.selectors.values():
            out.extend(group)
        out.extend(self.fallbacks)
        return list(dict.fromkeys(out))


def _host_key(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).netloc.lower()


def _cache_key(host: str) -> str:
    return hashlib.md5(host.encode()).hexdigest()[:12]


def discover_selectors_from_html(html: str, url: str) -> SelectorSchema:
    """Rule-based selector discovery from page structure."""
    host = _host_key(url)
    soup = BeautifulSoup(html, "html.parser")
    schema = SelectorSchema(host=host, fallbacks=list(DEFAULT_CONTACT_SELECTORS))

    for field, candidates in DEFAULT_FIELD_SELECTORS.items():
        found: list[str] = []
        for sel in candidates:
            if soup.select(sel):
                found.append(sel)
        if found:
            schema.selectors[field] = found

    # detect common patterns
    for el in soup.find_all(class_=re.compile(r"contact|phone|email", re.I))[:5]:
        if el.get("class"):
            cls = el.get("class")[0]
            sel = f".{cls}"
            if sel not in schema.fallbacks:
                schema.fallbacks.append(sel)

    with _cache_lock:
        _selector_cache[_cache_key(host)] = {
            "selectors": schema.selectors,
            "fallbacks": schema.fallbacks,
        }
    return schema


def get_cached_selectors(url: str) -> SelectorSchema | None:
    host = _host_key(url)
    with _cache_lock:
        data = _selector_cache.get(_cache_key(host))
    if not data:
        return None
    return SelectorSchema(host=host, selectors=data.get("selectors", {}), fallbacks=data.get("fallbacks", []))


def validate_selectors(html: str, selectors: list[str]) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    valid: list[str] = []
    for sel in selectors:
        try:
            if soup.select(sel):
                valid.append(sel)
        except Exception:
            continue
    return valid


def repair_selectors(html: str, url: str, broken: list[str]) -> list[str]:
    """Re-discover selectors when cached ones fail."""
    schema = discover_selectors_from_html(html, url)
    repaired = validate_selectors(html, schema.all_selectors())
    if repaired:
        return repaired
    return [s for s in DEFAULT_CONTACT_SELECTORS if s not in broken]


def ai_generate_selectors(html: str, url: str, groq_service=None) -> SelectorSchema | None:
    """Optional Groq-based selector generation for unknown layouts."""
    if groq_service is None:
        return discover_selectors_from_html(html, url)

    snippet = html[:12_000]
    prompt = (
        "Analyze this HTML and return JSON with CSS selectors for contact extraction.\n"
        'Format: {"email":["sel"],"phone":["sel"],"company":["sel"],"address":["sel"],"fallbacks":["sel"]}\n'
        f"URL: {url}\nHTML:\n{snippet}"
    )
    try:
        raw = groq_service._chat(prompt, max_tokens=512)
        if not raw:
            return discover_selectors_from_html(html, url)
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return discover_selectors_from_html(html, url)
        data = json.loads(m.group())
        host = _host_key(url)
        schema = SelectorSchema(
            host=host,
            selectors={k: v for k, v in data.items() if k != "fallbacks" and isinstance(v, list)},
            fallbacks=data.get("fallbacks", DEFAULT_CONTACT_SELECTORS),
        )
        with _cache_lock:
            _selector_cache[_cache_key(host)] = {
                "selectors": schema.selectors,
                "fallbacks": schema.fallbacks,
            }
        return schema
    except Exception as exc:
        logger.debug("AI selector generation failed: %s", exc)
        return discover_selectors_from_html(html, url)
