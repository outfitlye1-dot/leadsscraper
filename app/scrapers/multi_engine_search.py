"""Extra free internet search engines for lead discovery (no API keys)."""

from __future__ import annotations

import logging
import time
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

from app.scraper.utils.user_agents import get_random_user_agent
from app.scrapers.parser import unwrap_search_url
from app.utils.scrape_sources import should_skip_search_url

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://search.brave.com/search"
YAHOO_SEARCH_URL = "https://search.yahoo.com/search"
MOJEEK_SEARCH_URL = "https://www.mojeek.com/search"


def _host_ok(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return bool(host) and "." in host


def _clean_item(
    title: str | None,
    url: str | None,
    description: str | None,
    *,
    allow_maps_social: bool,
) -> dict | None:
    url = unwrap_search_url((url or "").strip())
    title = (title or "").strip()
    if not url or not title or not _host_ok(url):
        return None
    if should_skip_search_url(url, allow_maps_social=allow_maps_social):
        return None
    return {"title": title, "url": url, "description": (description or "").strip() or None}


def parse_brave_results(html: str, *, allow_maps_social: bool = False) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    for block in soup.select("div.snippet[data-type='web'], div.snippet"):
        link = block.select_one("a[href]")
        if not link:
            continue
        title_el = block.select_one(".title, a")
        snippet_el = block.select_one(".snippet-description, .snippet-content p, p")
        item = _clean_item(
            title_el.get_text(strip=True) if title_el else link.get_text(strip=True),
            link.get("href"),
            snippet_el.get_text(strip=True) if snippet_el else None,
            allow_maps_social=allow_maps_social,
        )
        if item:
            results.append(item)

    if results:
        return results

    # Fallback selectors (Brave HTML changes often)
    for link in soup.select("#results a[href^='http'], main a[href^='http']"):
        href = link.get("href") or ""
        if "brave.com" in href or "search?q=" in href:
            continue
        item = _clean_item(
            link.get_text(strip=True),
            href,
            None,
            allow_maps_social=allow_maps_social,
        )
        if item:
            results.append(item)
    return results


def parse_yahoo_results(html: str, *, allow_maps_social: bool = False) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    for block in soup.select("div.algo, div.dd.algo, li div.algo"):
        link = block.select_one("h3 a, a.ac-algo, a[href]")
        if not link:
            continue
        href = link.get("href") or ""
        # Yahoo wraps redirects: /RU=encoded
        if "/RU=" in href:
            try:
                part = href.split("/RU=", 1)[1]
                href = unquote(part.split("/RK=")[0].split("/RS=")[0])
            except Exception:
                pass
        snippet_el = block.select_one("p, span.fc-falcon, .compText p")
        item = _clean_item(
            link.get_text(strip=True),
            href,
            snippet_el.get_text(strip=True) if snippet_el else None,
            allow_maps_social=allow_maps_social,
        )
        if item:
            results.append(item)
    return results


def parse_mojeek_results(html: str, *, allow_maps_social: bool = False) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    for block in soup.select("ul.results-standard li, li.res, .results li"):
        link = block.select_one("a.ob, h2 a, a[href]")
        if not link:
            continue
        snippet_el = block.select_one("p.s, p, .snippet")
        item = _clean_item(
            link.get_text(strip=True),
            link.get("href"),
            snippet_el.get_text(strip=True) if snippet_el else None,
            allow_maps_social=allow_maps_social,
        )
        if item:
            results.append(item)
    return results


def parse_searxng_json(payload: dict, *, allow_maps_social: bool = False) -> list[dict]:
    results: list[dict] = []
    for row in payload.get("results") or []:
        item = _clean_item(
            row.get("title"),
            row.get("url") or row.get("link"),
            row.get("content") or row.get("snippet"),
            allow_maps_social=allow_maps_social,
        )
        if item:
            results.append(item)
    return results


class MultiEngineSearch:
    """Brave + Yahoo + Mojeek + optional SearXNG metasearch."""

    def __init__(self, timeout: float = 12.0, retries: int = 2):
        self.timeout = timeout
        self.retries = max(1, retries)
        self._session = requests.Session()

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _get(self, url: str, params: dict | None = None) -> str | None:
        for attempt in range(1, self.retries + 1):
            try:
                response = self._session.get(
                    url,
                    params=params,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                if response.status_code >= 400:
                    if attempt < self.retries:
                        time.sleep(0.4 * attempt)
                        continue
                    return None
                return response.text
            except Exception as exc:
                logger.debug("Search fetch failed (%s): %s", url, exc)
                if attempt < self.retries:
                    time.sleep(0.4 * attempt)
        return None

    def search_brave(self, query: str, *, allow_maps_social: bool = False) -> list[dict]:
        html = self._get(BRAVE_SEARCH_URL, {"q": query, "source": "web"})
        if not html:
            return []
        return parse_brave_results(html, allow_maps_social=allow_maps_social)

    def search_yahoo(self, query: str, *, allow_maps_social: bool = False) -> list[dict]:
        html = self._get(YAHOO_SEARCH_URL, {"p": query, "n": 30})
        if not html:
            return []
        return parse_yahoo_results(html, allow_maps_social=allow_maps_social)

    def search_mojeek(self, query: str, *, allow_maps_social: bool = False) -> list[dict]:
        html = self._get(MOJEEK_SEARCH_URL, {"q": query})
        if not html:
            return []
        return parse_mojeek_results(html, allow_maps_social=allow_maps_social)

    def search_searxng(
        self,
        query: str,
        instance_url: str,
        *,
        allow_maps_social: bool = False,
    ) -> list[dict]:
        base = instance_url.rstrip("/")
        for attempt in range(1, self.retries + 1):
            try:
                response = self._session.get(
                    f"{base}/search",
                    params={"q": query, "format": "json", "language": "en"},
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                if response.status_code >= 400:
                    if attempt < self.retries:
                        time.sleep(0.4 * attempt)
                        continue
                    return []
                data = response.json()
                return parse_searxng_json(data, allow_maps_social=allow_maps_social)
            except Exception as exc:
                logger.debug("SearXNG search failed (%s): %s", base, exc)
                if attempt < self.retries:
                    time.sleep(0.4 * attempt)
        return []
