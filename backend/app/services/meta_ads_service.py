"""Meta (Facebook/Instagram) Ad Library lead discovery."""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.lead import LeadStatus
from app.scrapers.fetcher import PageFetcher
from app.utils.meta_ads_country import build_ad_library_url, location_to_iso_country
from app.utils.scrape_sources import map_meta_ad_to_lead, parse_location_parts

logger = logging.getLogger(__name__)

_ADVERTISER_PATTERNS = (
    re.compile(r'"page_name"\s*:\s*"([^"\\]+)"'),
    re.compile(r'"advertiser_name"\s*:\s*"([^"\\]+)"'),
    re.compile(r'"pageName"\s*:\s*"([^"\\]+)"'),
    re.compile(r'"advertiserName"\s*:\s*"([^"\\]+)"'),
)
_LINK_PATTERNS = (
    re.compile(r'"link_url"\s*:\s*"(https?://[^"\\]+)"'),
    re.compile(r'"landingUrl"\s*:\s*"(https?://[^"\\]+)"'),
    re.compile(r'"linkUrl"\s*:\s*"(https?://[^"\\]+)"'),
)
_PAGE_URL_PATTERNS = (
    re.compile(r'"page_url"\s*:\s*"(https?://(?:www\.)?facebook\.com/[^"\\]+)"'),
    re.compile(r'"pageUrl"\s*:\s*"(https?://(?:www\.)?facebook\.com/[^"\\]+)"'),
)
_IG_PATTERNS = (
    re.compile(r'"instagram_username"\s*:\s*"([^"\\]+)"'),
    re.compile(r'"instagramUsername"\s*:\s*"([^"\\]+)"'),
)
_AD_TEXT_PATTERNS = (
    re.compile(r'"ad_creative_bodies"\s*:\s*\[\s*"([^"]*)"'),
    re.compile(r'"adText"\s*:\s*"([^"\\]+)"'),
    re.compile(r'"body"\s*:\s*"([^"\\]+)"'),
)


def _clean_name(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\\n", " ").replace("\\/", "/").strip()


def _is_junk_landing(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if not host:
        return True
    blocked = (
        "facebook.com",
        "fb.com",
        "instagram.com",
        "fb.me",
        "l.facebook.com",
        "google.com",
        "play.google.com",
        "apps.apple.com",
    )
    return any(b in host for b in blocked)


class MetaAdsService:
    def search_leads(
        self,
        keyword: str,
        location: str,
        limit: int,
        search_query: str | None = None,
        *,
        user_id: int | None = None,
        db: Session | None = None,
    ) -> list[dict]:
        query = (search_query or keyword or "").strip()
        if not query or limit <= 0:
            return []

        country_iso = location_to_iso_country(location)
        per_query = min(max(limit * 2, 20), 200)

        if user_id is not None and db is not None:
            try:
                apify_leads = self._scrape_via_apify(
                    user_id, db, query, country_iso, per_query, location
                )
                if apify_leads:
                    return apify_leads[:limit]
            except Exception as exc:
                logger.warning("Meta Ads Apify scrape failed, using fallback: %s", exc)

        native_leads = self._scrape_native(query, country_iso, per_query, location)
        return native_leads[:limit]

    def _scrape_via_apify(
        self,
        user_id: int,
        db: Session,
        query: str,
        country_iso: str,
        max_ads: int,
        location: str,
    ) -> list[dict]:
        from apify_client import ApifyClient
        from app.models.user_api_key import ApiProvider
        from app.services.api_key_rotation_service import ApiKeyRotationService

        settings = get_settings()
        actor_id = settings.APIFY_META_ADS_ACTOR_ID
        if not actor_id:
            return []

        rotation = ApiKeyRotationService(db)
        tokens = rotation.get_user_tokens(user_id, ApiProvider.apify)
        if not tokens:
            return []

        run_input = {
            "queries": [query],
            "countries": [country_iso],
            "maxAdsPerQuery": max_ads,
            "adType": "ALL",
            "activeStatus": "active",
        }

        def run_with_token(token: str) -> list[dict]:
            client = ApifyClient(token)
            run = client.actor(actor_id).call(run_input=run_input)
            dataset_id = (
                run["defaultDatasetId"]
                if isinstance(run, dict)
                else run.default_dataset_id
            )
            items = list(client.dataset(dataset_id).iterate_items())
            return self._map_apify_items(items, location)

        return rotation.execute_with_rotation(user_id, ApiProvider.apify, run_with_token)

    def _map_apify_items(self, items: list[dict], location: str) -> list[dict]:
        leads: list[dict] = []
        seen_pages: set[str] = set()

        for item in items:
            page_key = (
                str(item.get("pageId") or item.get("searchPageId") or "")
                or (item.get("pageUrl") or item.get("page_url") or "")
                or _clean_name(
                    item.get("advertiserName")
                    or item.get("advertiser")
                    or item.get("pageName")
                    or item.get("page_name")
                ).lower()
            )
            if page_key and page_key in seen_pages:
                continue
            if page_key:
                seen_pages.add(page_key)

            mapped = map_meta_ad_to_lead(
                {
                    "company_name": item.get("advertiserName")
                    or item.get("advertiser")
                    or item.get("pageName")
                    or item.get("page_name"),
                    "website": item.get("landingUrl")
                    or item.get("linkUrl")
                    or item.get("link_url"),
                    "facebook_url": item.get("pageUrl") or item.get("page_url"),
                    "instagram_url": self._instagram_url_from_item(item),
                    "ad_text": item.get("adText")
                    or item.get("body")
                    or (
                        (item.get("ad_creative_bodies") or [None])[0]
                        if isinstance(item.get("ad_creative_bodies"), list)
                        else item.get("ad_creative_bodies")
                    ),
                    "platforms": item.get("platforms") or item.get("publisher_platforms"),
                    "is_active": item.get("isActive", True),
                },
                location,
            )
            if mapped:
                leads.append(mapped)

        return leads

    def _instagram_url_from_item(self, item: dict) -> str | None:
        username = item.get("instagramUsername") or item.get("instagram_username")
        if username:
            return f"https://www.instagram.com/{username.strip().lstrip('@')}/"
        platforms = item.get("platforms") or item.get("publisher_platforms") or []
        if isinstance(platforms, list) and any(
            str(p).lower() == "instagram" for p in platforms
        ):
            page_url = item.get("pageUrl") or item.get("page_url")
            if page_url:
                return None
        return None

    def _scrape_native(self, query: str, country_iso: str, max_ads: int, location: str) -> list[dict]:
        url = build_ad_library_url(query, country_iso)
        fetcher = PageFetcher(timeout=25.0, use_playwright=True)
        html, _ = fetcher.fetch(url)
        if not html:
            logger.warning("Meta Ad Library fetch returned empty HTML for %s", query)
            return []

        raw_items = self._parse_embedded_ads(html, max_ads)
        if not raw_items:
            raw_items = self._parse_regex_ads(html, max_ads)

        leads: list[dict] = []
        seen: set[str] = set()
        for raw in raw_items:
            key = (raw.get("company_name") or "").lower()
            if not key or key in seen:
                continue
            seen.add(key)
            mapped = map_meta_ad_to_lead(raw, location)
            if mapped:
                leads.append(mapped)
        return leads

    def _parse_embedded_ads(self, html: str, max_ads: int) -> list[dict]:
        items: list[dict] = []
        for match in re.finditer(r'\{"ad_archive_id"[^}]{20,800}\}', html):
            try:
                blob = json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
            company = _clean_name(blob.get("page_name") or blob.get("pageName"))
            if not company:
                continue
            link = blob.get("link_url") or blob.get("linkUrl")
            if link and _is_junk_landing(link):
                link = None
            items.append(
                {
                    "company_name": company,
                    "website": link,
                    "facebook_url": blob.get("page_url") or blob.get("pageUrl"),
                    "ad_text": None,
                    "is_active": True,
                }
            )
            if len(items) >= max_ads:
                break
        return items

    def _parse_regex_ads(self, html: str, max_ads: int) -> list[dict]:
        names: list[str] = []
        for pattern in _ADVERTISER_PATTERNS:
            names.extend(_clean_name(m) for m in pattern.findall(html))
        names = [n for n in names if n and len(n) > 2]

        links = []
        for pattern in _LINK_PATTERNS:
            links.extend(pattern.findall(html))
        links = [u for u in links if not _is_junk_landing(u)]

        page_urls = []
        for pattern in _PAGE_URL_PATTERNS:
            page_urls.extend(pattern.findall(html))

        ig_users = []
        for pattern in _IG_PATTERNS:
            ig_users.extend(pattern.findall(html))

        ad_texts = []
        for pattern in _AD_TEXT_PATTERNS:
            ad_texts.extend(_clean_name(m) for m in pattern.findall(html))

        items: list[dict] = []
        for idx, name in enumerate(names):
            if len(items) >= max_ads:
                break
            ig_url = None
            if idx < len(ig_users):
                ig_url = f"https://www.instagram.com/{ig_users[idx].strip().lstrip('@')}/"
            items.append(
                {
                    "company_name": name,
                    "website": links[idx] if idx < len(links) else None,
                    "facebook_url": page_urls[idx] if idx < len(page_urls) else None,
                    "instagram_url": ig_url,
                    "ad_text": ad_texts[idx] if idx < len(ad_texts) else None,
                    "is_active": True,
                }
            )
        return items
