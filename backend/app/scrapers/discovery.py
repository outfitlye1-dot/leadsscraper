import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

import requests
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.scraper.utils.user_agents import get_random_user_agent
from app.scraper.utils.workers import compute_search_workers
from app.scrapers.multi_engine_search import MultiEngineSearch
from app.scrapers.parser import parse_duckduckgo_results, unwrap_search_url
from app.utils.scrape_sources import should_skip_search_url

logger = logging.getLogger(__name__)

BING_SEARCH_URL = "https://www.bing.com/search"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"


def _call_with_timeout(fn: Callable[[], list[dict]], seconds: float) -> list[dict]:
    """Run a search call with a hard wall-clock limit (DDGS has no native timeout)."""
    if seconds <= 0.5:
        return []
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(fn)
        try:
            return future.result(timeout=seconds) or []
        except TimeoutError:
            logger.warning("Search call timed out after %.1fs", seconds)
            return []
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def parse_bing_results(html: str, *, allow_maps_social: bool = False) -> list[dict]:
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
        if url and not should_skip_search_url(url, allow_maps_social=allow_maps_social):
            results.append({"title": title, "url": url, "description": description})

    if results:
        return results

    for link in soup.select("#b_results h2 a"):
        url = unwrap_search_url(link.get("href") or "")
        title = link.get_text(strip=True)
        if url and not should_skip_search_url(url, allow_maps_social=allow_maps_social):
            results.append({"title": title, "url": url, "description": None})

    return results


class SearchDiscovery:
    """Discover business URLs via DDGS + Bing + Brave/Yahoo/Mojeek (+ optional SearXNG)."""

    def __init__(self, timeout: float | None = None):
        settings = get_settings()
        # Firm ceiling — slow engines must not hang the whole scrape
        self.timeout = timeout if timeout is not None else min(max(settings.SCRAPER_TIMEOUT, 5.0), 8.0)
        self.bing_pages = 1 if settings.SCRAPER_FAST_MODE else max(1, min(settings.SCRAPER_BING_PAGES, 2))
        self.retries = 1 if settings.SCRAPER_FAST_MODE else max(1, min(settings.SCRAPER_FETCH_RETRIES, 2))
        self.extra_engines = {
            e.strip().lower()
            for e in (settings.SCRAPER_EXTRA_ENGINES or "").split(",")
            if e.strip()
        }
        self.searxng_url = (settings.SCRAPER_SEARXNG_URL or "").strip()
        self._multi = MultiEngineSearch(timeout=self.timeout, retries=self.retries)
        self._session = requests.Session()
        self._refresh_headers()

    def _refresh_headers(self) -> None:
        self._session.headers.update(
            {
                "User-Agent": get_random_user_agent(),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def _engine_jobs(self, query: str, limit: int, allow_maps_social: bool):
        """Build (name, callable) search jobs — HTML engines first, DDGS last (can hang)."""
        q = query
        lim = limit
        allow = allow_maps_social
        jobs: list[tuple[str, Callable[[], list[dict]]]] = [
            ("bing", lambda: self._search_bing(q, allow)),
        ]
        if "brave" in self.extra_engines:
            jobs.append(("brave", lambda: self._multi.search_brave(q, allow_maps_social=allow)))
        if "yahoo" in self.extra_engines:
            jobs.append(("yahoo", lambda: self._multi.search_yahoo(q, allow_maps_social=allow)))
        # Skip mojeek by default — often 403 and wastes worker slots
        if "mojeek" in self.extra_engines and get_settings().SCRAPER_FAST_MODE is False:
            jobs.append(("mojeek", lambda: self._multi.search_mojeek(q, allow_maps_social=allow)))
        if self.searxng_url:
            searx = self.searxng_url
            jobs.append(
                (
                    "searxng",
                    lambda: self._multi.search_searxng(q, searx, allow_maps_social=allow),
                )
            )
        # DDGS optional — good results but can hang; run only if we still need more AND time left
        if not get_settings().SCRAPER_FAST_MODE:
            jobs.append(("ddgs", lambda: self._search_ddgs_single(q, lim, allow)))
        return jobs

    def search(
        self,
        keyword: str = "",
        location: str = "",
        limit: int = 20,
        search_query: str | None = None,
        *,
        prefer_no_website: bool = False,
        on_batch: Callable[[list[dict]], None] | None = None,
        deadline: float | None = None,
        metrics=None,
    ) -> list[dict]:
        queries = self._build_queries(
            keyword, location, limit, search_query, prefer_no_website=prefer_no_website
        )
        if not queries:
            return []

        results: list[dict] = []
        seen_urls: set[str] = set()
        allow_maps_social = prefer_no_website
        engine_hits: dict[str, int] = {}
        settings = get_settings()
        fast = bool(settings.SCRAPER_FAST_MODE)

        def _merge_batch(batch: list[dict], engine: str = "") -> list[dict]:
            fresh: list[dict] = []
            for item in batch:
                if len(results) >= limit:
                    return fresh
                url = item.get("url") or ""
                if not url or url in seen_urls:
                    continue
                if should_skip_search_url(url, allow_maps_social=allow_maps_social):
                    continue
                seen_urls.add(url)
                results.append(item)
                fresh.append(item)
                if engine:
                    engine_hits[engine] = engine_hits.get(engine, 0) + 1
            return fresh

        all_jobs: list[tuple[str, str, Callable[[], list[dict]]]] = []
        # In fast mode prefer HTML DDG + Bing only — flooding Brave/Yahoo triggers empty SERPs.
        # DDGS is reserved for sequential fallback (below) so executor.shutdown doesn't break it.
        for query in queries:
            if fast:
                q = query
                all_jobs.append(("ddg_html", query, lambda q=q: self._search_ddg_html(q)))
                all_jobs.append(("bing", query, lambda q=q: self._search_bing(q, allow_maps_social)))
            else:
                for name, fn in self._engine_jobs(query, limit, allow_maps_social):
                    all_jobs.append((name, query, fn))
                q = query
                all_jobs.append(("ddg_html", query, lambda q=q: self._search_ddg_html(q)))

        workers = min(compute_search_workers(len(all_jobs)), 6 if fast else 12)
        # Wall-clock for discovery — leave room for crawl before outer job timeout
        search_budget = 12.0 if fast else 22.0
        if deadline is not None:
            search_budget = max(4.0, min(search_budget, deadline - time.monotonic() - 8.0))
        disc_deadline = time.monotonic() + search_budget

        logger.info(
            "Internet discovery: %s queries · %s jobs · %s workers · budget=%.0fs · engines=%s",
            len(queries),
            len(all_jobs),
            workers,
            search_budget,
            sorted({j[0] for j in all_jobs}),
        )

        if metrics is not None:
            metrics.set("active_workers", workers)
            metrics.set("queue_size", len(all_jobs))

        executor = ThreadPoolExecutor(max_workers=workers)
        futures = {executor.submit(fn): name for name, _query, fn in all_jobs}
        pending = set(futures.keys())
        try:
            while pending and len(results) < limit and time.monotonic() < disc_deadline:
                done, pending = wait(pending, timeout=0.35, return_when=FIRST_COMPLETED)
                for future in done:
                    engine = futures.get(future, "?")
                    try:
                        fresh = _merge_batch(future.result(timeout=0) or [], engine)
                        if fresh and on_batch:
                            on_batch(fresh)
                        if metrics is not None and fresh:
                            metrics.inc("strategy_http", 1)
                    except Exception as exc:
                        logger.warning("Parallel search failed (%s): %s", engine, exc)
                        if metrics is not None:
                            metrics.inc("retry_count")
                if metrics is not None:
                    metrics.set("queue_size", len(pending))
                    metrics.set("active_workers", min(workers, max(1, len(pending))))
                # Early exit once we have enough usable seeds
                if len(results) >= max(limit, 6):
                    break
        finally:
            for fut in pending:
                fut.cancel()
            for fut in futures:
                fut.cancel()
            # NEVER wait=True — stuck network threads (DDGS) would hang the scrape forever
            executor.shutdown(wait=False, cancel_futures=True)
            if metrics is not None:
                metrics.set("active_workers", 0)
                metrics.set("queue_size", 0)

        # Lightweight sequential HTML fallback — always try once even if parallel got a few
        if len(results) < max(5, limit // 2) and time.monotonic() < disc_deadline:
            for query in queries[:2]:
                remain = disc_deadline - time.monotonic()
                if len(results) >= limit or remain < 1.5:
                    break
                try:
                    # Small pause reduces DDG rate-limit empties after parallel burst
                    time.sleep(min(0.35, max(0.0, remain - 1.0)))
                    remain = disc_deadline - time.monotonic()
                    for item in _call_with_timeout(
                        lambda q=query: self._search_ddg_html(q), min(6.0, remain)
                    ):
                        fresh = _merge_batch([item], "ddg_html_seq")
                        if fresh and on_batch:
                            on_batch(fresh)
                        if len(results) >= limit:
                            break
                except Exception as exc:
                    logger.warning("DDG HTML fallback failed: %s", exc)
                remain = disc_deadline - time.monotonic()
                if remain < 1.5:
                    break
                try:
                    batch = _call_with_timeout(
                        lambda q=query: self._search_bing(q, allow_maps_social),
                        min(6.0, remain),
                    )
                    if batch:
                        _merge_batch(batch, "bing_retry")
                except Exception as exc:
                    logger.warning("Bing retry failed: %s", exc)
            # DDGS last-resort — works when Bing captcha / DDG HTML timeout
            if len(results) < 3 and time.monotonic() < disc_deadline:
                for query in queries[:2]:
                    remain = disc_deadline - time.monotonic()
                    if len(results) >= limit or remain < 2.0:
                        break
                    try:
                        batch = _call_with_timeout(
                            lambda q=query: self._search_ddgs_single(
                                q, limit, allow_maps_social
                            ),
                            min(10.0, remain),
                        )
                        if batch:
                            fresh = _merge_batch(batch, "ddgs_fallback")
                            if fresh and on_batch:
                                on_batch(fresh)
                            logger.info("DDGS fallback recovered %s URL(s)", len(fresh))
                    except Exception as exc:
                        logger.warning("DDGS fallback failed: %s", exc)
            # Last-resort: one more diverse wording if still thin
            if len(results) < 3 and time.monotonic() < disc_deadline:
                kw = (keyword or "").strip()
                loc_city = (location or "").split(",")[0].strip()
                if kw and loc_city:
                    for extra_q in (
                        f"{kw} {loc_city} official site",
                        f"{kw} {loc_city} coffee shop" if "cafe" in kw.lower() or "coffee" in kw.lower() else f"{kw} {loc_city} business",
                    ):
                        remain = disc_deadline - time.monotonic()
                        if len(results) >= limit or remain < 1.5:
                            break
                        if any(extra_q.lower() == q.lower() for q in queries):
                            continue
                        try:
                            time.sleep(min(0.25, max(0.0, remain - 1.0)))
                            remain = disc_deadline - time.monotonic()
                            _merge_batch(
                                _call_with_timeout(
                                    lambda q=extra_q: self._search_ddg_html(q),
                                    min(5.0, remain),
                                ),
                                "ddg_extra",
                            )
                        except Exception as exc:
                            logger.debug("Extra DDG query failed: %s", exc)

        logger.info(
            "Internet discovery found %s URLs · engine hits=%s",
            len(results),
            engine_hits,
        )
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
        keyword = keyword.strip()
        location = location.strip()
        city = location.split(",")[0].strip() if location else ""
        queries: list[str] = []

        def _add(*parts: str) -> None:
            q = " ".join(p for p in parts if p).strip()
            if not q:
                return
            # Drop near-duplicates (same tokens)
            key = " ".join(sorted(q.lower().replace(",", " ").split()))
            existing_keys = {
                " ".join(sorted(x.lower().replace(",", " ").split())) for x in queries
            }
            if key in existing_keys:
                return
            queries.append(q)

        base = (search_query or "").strip()
        for junk in (
            " contact email phone whatsapp",
            " email phone whatsapp",
            " contact email phone",
            " contact email",
        ):
            if base.lower().endswith(junk.strip()):
                base = base[: -len(junk)].strip()
                break

        # Primary: short business-website oriented queries (listicles hate these)
        if keyword and city:
            _add(keyword, city, "website")
            _add(keyword, city)
        elif keyword and location:
            _add(keyword, location, "website")
            _add(keyword, location)
        elif keyword:
            _add(keyword, "website")
            _add(keyword)

        if base:
            # Only add UI query if it isn't already covered
            _add(base)
            if city and city.lower() not in base.lower():
                _add(base, city, "website")

        if prefer_no_website and keyword and (city or location):
            loc = city or location
            _add(keyword, loc, "phone")
            _add(keyword, loc, "facebook")

        # Fast mode: fewer queries = less engine rate-limiting
        cap = 2 if get_settings().SCRAPER_FAST_MODE else 4
        return queries[:cap]

    def _search_ddgs_single(
        self, query: str, limit: int, allow_maps_social: bool = False
    ) -> list[dict]:
        return self._search_ddgs([query], limit, allow_maps_social=allow_maps_social)

    def _search_ddgs(
        self,
        queries: list[str],
        limit: int,
        *,
        allow_maps_social: bool = False,
    ) -> list[dict]:
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
                        items = ddgs.text(query, max_results=min(max(limit, 20), 50))
                        for item in items:
                            url = unwrap_search_url(
                                item.get("href") or item.get("link") or ""
                            )
                            title = item.get("title") or ""
                            description = item.get("body") or item.get("snippet")
                            if (
                                url
                                and title
                                and not should_skip_search_url(
                                    url, allow_maps_social=allow_maps_social
                                )
                            ):
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

    def _search_bing(self, query: str, allow_maps_social: bool = False) -> list[dict]:
        results: list[dict] = []
        for page in range(self.bing_pages):
            offset = page * 10 + 1
            batch = self._search_bing_page(query, offset, allow_maps_social=allow_maps_social)
            if not batch:
                break
            results.extend(batch)
            if len(batch) < 8:
                break
        return results

    def _search_bing_page(
        self, query: str, first: int, *, allow_maps_social: bool = False
    ) -> list[dict]:
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
                return parse_bing_results(response.text, allow_maps_social=allow_maps_social)
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
