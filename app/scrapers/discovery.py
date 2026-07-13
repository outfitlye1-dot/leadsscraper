import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.scraper.utils.user_agents import get_random_user_agent
from app.scraper.utils.workers import compute_search_workers
from app.scrapers.parser import parse_duckduckgo_results, unwrap_search_url
from app.utils.scrape_sources import should_skip_search_url

logger = logging.getLogger(__name__)

BING_SEARCH_URL = "https://www.bing.com/search"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"


def parse_bing_results(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    for block in soup.select("li.b_algo"):
        link = block.select_one("h2 a")
        if not link:
            continue
        url = unwrap_search_url(link.get("href") or "")
        title = link.get_text(strip=True)
        snippet_el = block.select_one("div.b_caption p, p")
        description = snippet_el.get_text(strip=True) if snippet_el else None
        if url and not should_skip_search_url(url):
            results.append({"title": title, "url": url, "description": description})

    if results:
        return results

    for link in soup.select("#b_results h2 a"):
        url = unwrap_search_url(link.get("href") or "")
        title = link.get_text(strip=True)
        if url and not should_skip_search_url(url):
            results.append({"title": title, "url": url, "description": None})

    return results


SEARCH_EXCLUDE_SITES = (
    "-site:facebook.com -site:instagram.com -site:linkedin.com "
    "-site:yelp.com -site:tripadvisor.com -site:wikipedia.org "
    "-site:reddit.com -site:quora.com -site:medium.com -site:clutch.co "
    "-site:justdial.com -site:yellowpages.com -site:pinterest.com "
    "-site:indiamart.com -site:alibaba.com -site:tradeindia.com "
    "-site:kompass.com -site:bark.com -site:thumbtack.com"
)


class SearchDiscovery:
    """Discover business URLs via DDGS API, Bing HTML, or DuckDuckGo HTML fallback."""

    def __init__(self, timeout: float | None = None):
        settings = get_settings()
        self.timeout = timeout if timeout is not None else max(settings.SCRAPER_TIMEOUT, 12.0)
        self.bing_pages = settings.SCRAPER_BING_PAGES
        self.retries = settings.SCRAPER_FETCH_RETRIES
        self._session = requests.Session()
        self._refresh_headers()

    def _refresh_headers(self) -> None:
        self._session.headers.update(
            {
                "User-Agent": get_random_user_agent(),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def search(
        self,
        keyword: str = "",
        location: str = "",
        limit: int = 20,
        search_query: str | None = None,
        *,
        prefer_no_website: bool = False,
    ) -> list[dict]:
        queries = self._build_queries(
            keyword, location, limit, search_query, prefer_no_website=prefer_no_website
        )
        if not queries:
            return []

        results: list[dict] = []
        seen_urls: set[str] = set()

        def _merge_batch(batch: list[dict]) -> None:
            for item in batch:
                if len(results) >= limit:
                    return
                url = item.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(item)

        workers = compute_search_workers(len(queries))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for query in queries:
                futures.append(executor.submit(self._search_ddgs_single, query, limit))
                futures.append(executor.submit(self._search_bing, query))
            for future in as_completed(futures):
                if len(results) >= limit:
                    break
                try:
                    _merge_batch(future.result())
                except Exception as exc:
                    logger.warning("Parallel search failed: %s", exc)

        if len(results) < limit:
            for query in queries:
                if len(results) >= limit:
                    break
                for item in self._search_ddg_html(query):
                    url = item.get("url") or ""
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    results.append(item)
                    if len(results) >= limit:
                        break

        return results[:limit]

    def _build_queries(
        self,
        keyword: str,
        location: str,
        limit: int,
        search_query: str | None,
        *,
        prefer_no_website: bool = False,
    ) -> list[str]:
        if search_query and search_query.strip():
            base = search_query.strip()
            loc = location.strip()
            queries = [f"{base} {SEARCH_EXCLUDE_SITES}".strip()]
            if "contact" not in base.lower() and "email" not in base.lower():
                queries.append(f"{base} contact email phone {SEARCH_EXCLUDE_SITES}".strip())
            if "whatsapp" not in base.lower():
                queries.append(f"{base} whatsapp phone number {SEARCH_EXCLUDE_SITES}".strip())
            if loc and loc.lower() not in base.lower():
                queries.append(f"{base} {loc} {SEARCH_EXCLUDE_SITES}".strip())
            if limit > 10:
                queries.append(f"{base} business website {SEARCH_EXCLUDE_SITES}".strip())
            return list(dict.fromkeys(queries))

        keyword = keyword.strip()
        location = location.strip()
        if not keyword:
            return []

        exclude = SEARCH_EXCLUDE_SITES
        city = location.split(",")[0].strip() if location else ""
        queries: list[str] = []
        if prefer_no_website and location:
            queries.extend(
                [
                    f"{keyword} {location} site:google.com/maps phone",
                    f"{keyword} {city} site:facebook.com phone whatsapp",
                    f"{keyword} {location} facebook page phone -wordpress",
                ]
            )
        if location:
            if limit <= 5:
                queries.append(f"{keyword} {location} {exclude}".strip())
            else:
                queries.extend(
                    [
                        f"{keyword} {location} {exclude}".strip(),
                        f"{keyword} in {location} contact email phone {exclude}".strip(),
                        f"{keyword} {location} google maps phone email {exclude}".strip(),
                        f"{keyword} near {location} business phone number {exclude}".strip(),
                        f"{keyword} {location} business website {exclude}".strip(),
                    ]
                )
        else:
            queries.extend(
                [
                    f"{keyword} {exclude}".strip(),
                    f"{keyword} contact email phone {exclude}".strip(),
                ]
            )
        return list(dict.fromkeys(queries))

    def _search_ddgs_single(self, query: str, limit: int) -> list[dict]:
        return self._search_ddgs([query], limit)

    def _search_ddgs(self, queries: list[str], limit: int) -> list[dict]:
        results: list[dict] = []
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                logger.warning("ddgs package not installed")
                return []

        try:
            with DDGS() as ddgs:
                for query in queries:
                    if len(results) >= limit:
                        break
                    try:
                        items = ddgs.text(query, max_results=min(limit, 50))
                        for item in items:
                            url = unwrap_search_url(
                                item.get("href") or item.get("link") or ""
                            )
                            title = item.get("title") or ""
                            description = item.get("body") or item.get("snippet")
                            if url and title and not should_skip_search_url(url):
                                results.append(
                                    {"title": title, "url": url, "description": description}
                                )
                            if len(results) >= limit:
                                break
                    except Exception as exc:
                        logger.warning("DDGS query failed (%s): %s", query, exc)
        except Exception as exc:
            logger.warning("DDGS search failed: %s", exc)

        return results

    def _search_bing(self, query: str) -> list[dict]:
        results: list[dict] = []
        for page in range(self.bing_pages):
            offset = page * 10 + 1
            batch = self._search_bing_page(query, offset)
            if not batch:
                break
            results.extend(batch)
            if len(batch) < 8:
                break
        return results

    def _search_bing_page(self, query: str, first: int) -> list[dict]:
        self._refresh_headers()
        for attempt in range(1, self.retries + 1):
            try:
                response = self._session.get(
                    BING_SEARCH_URL,
                    params={"q": query, "count": 30, "first": first},
                    timeout=self.timeout,
                )
                if response.status_code >= 400:
                    if attempt < self.retries:
                        time.sleep(0.5 * attempt)
                        continue
                    return []
                return parse_bing_results(response.text)
            except Exception as exc:
                logger.debug("Bing page fetch failed (first=%s): %s", first, exc)
                if attempt < self.retries:
                    time.sleep(0.5 * attempt)
        return []

    def _search_ddg_html(self, query: str) -> list[dict]:
        for attempt in range(1, self.retries + 1):
            try:
                response = self._session.post(
                    DDG_HTML_URL,
                    data={"q": query, "b": "", "kl": "us-en"},
                    timeout=self.timeout,
                )
                if response.status_code >= 400:
                    if attempt < self.retries:
                        time.sleep(0.5 * attempt)
                        continue
                    return []
                parsed = parse_duckduckgo_results(response.text)
                for item in parsed:
                    item["url"] = unwrap_search_url(item.get("url") or "")
                return [item for item in parsed if item.get("url")]
            except Exception as exc:
                logger.debug("DDG HTML search failed (attempt %s): %s", attempt, exc)
                if attempt < self.retries:
                    time.sleep(0.5 * attempt)
        return []
