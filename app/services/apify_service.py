import re

from apify_client import ApifyClient
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.lead import LeadStatus
from app.repositories.lead_repository import LeadRepository
from app.services.web_search_service import WebSearchService
from app.utils.scrape_sources import (
    ScrapeSourceMode,
    dedupe_leads,
)
from app.utils.website_utils import is_google_maps_url, normalize_website_field


class ApifyService:
    def __init__(self, lead_repository: LeadRepository):
        self.lead_repository = lead_repository
        self.web_search_service = WebSearchService()

    def scrape_leads(self, user_id: int, keyword: str, location: str, limit: int) -> dict:
        leads_data = self.collect_leads_data(
            user_id, keyword, location, limit, ScrapeSourceMode.google_maps
        )
        if isinstance(leads_data, dict):
            return leads_data

        from app.services.lead_service import LeadService

        lead_service = LeadService(self.lead_repository.db)
        saved, imported, skipped, intel_stats = lead_service.save_scraped_leads(user_id, leads_data)
        msg = f"Successfully imported {imported} leads."
        if skipped:
            msg += f" Skipped {skipped} duplicate(s)."
        return {
            "success": True,
            "count": imported,
            "skipped_duplicates": skipped,
            "message": msg,
            "intelligence_stats": intel_stats,
        }

    def collect_leads_data(
        self,
        user_id: int,
        keyword: str,
        location: str,
        limit: int,
        scrape_source: ScrapeSourceMode = ScrapeSourceMode.all,
    ) -> list[dict] | dict:
        from app.models.user_api_key import ApiProvider
        from app.services.api_key_rotation_service import ApiKeyRotationService

        settings = get_settings()
        keyword = keyword.strip()
        location = self._normalize_location(location.strip())

        needs_maps = scrape_source in (ScrapeSourceMode.all, ScrapeSourceMode.google_maps)
        needs_web = scrape_source in (ScrapeSourceMode.all, ScrapeSourceMode.google_search)

        if needs_maps and not ApiKeyRotationService(self.lead_repository.db).get_user_tokens(
            user_id, ApiProvider.apify
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apify API key required. Add your own Apify token in Settings → API Keys.",
            )

        rotation = ApiKeyRotationService(self.lead_repository.db)

        maps_leads: list[dict] = []
        search_leads: list[dict] = []
        errors: list[str] = []

        per_source_limit = limit if scrape_source != ScrapeSourceMode.all else max(limit // 2, 10)

        if needs_maps:
            try:
                def run_maps(token: str) -> list[dict]:
                    client = ApifyClient(token)
                    return self._scrape_google_maps(
                        client, settings.APIFY_ACTOR_ID, keyword, location, per_source_limit
                    )

                maps_leads = rotation.execute_with_rotation(user_id, ApiProvider.apify, run_maps)
            except Exception as exc:
                errors.append(f"Google Maps: {exc}")

        if needs_web:
            try:
                search_leads = self.web_search_service.search_leads(
                    keyword, location, per_source_limit
                )
            except Exception as exc:
                errors.append(f"Internet (Scrapy): {exc}")

        if not maps_leads and not search_leads:
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Scraping failed. {'; '.join(errors)}",
                )
            return {
                "success": True,
                "count": 0,
                "message": (
                    f"No leads found for '{keyword}' in '{location}'. "
                    "Try a broader keyword and 'City, Country' location."
                ),
            }

        combined = dedupe_leads(maps_leads + search_leads)[:limit]

        if not combined:
            return {
                "success": True,
                "count": 0,
                "message": f"No leads found for '{keyword}' in '{location}'.",
            }

        return combined

    def count_by_source(self, leads: list[dict]) -> tuple[int, int, int]:
        maps = 0
        search = 0
        meta = 0
        for lead in leads:
            src = lead.get("source") or ""
            if "meta_ads" in src:
                meta += 1
            if "apify" in src:
                maps += 1
            if "web_search" in src or "google_search" in src:
                search += 1
        return maps, search, meta

    def _scrape_google_maps(
        self,
        client: ApifyClient,
        actor_id: str,
        keyword: str,
        location: str,
        limit: int,
    ) -> list[dict]:
        search_variants = [
            [keyword],
            [f"{keyword} in {location}"],
            [keyword, f"{keyword} near {location}"],
        ]

        dataset_items: list[dict] = []
        last_error: Exception | None = None

        for search_terms in search_variants:
            try:
                dataset_items = self._run_maps_actor(
                    client, actor_id, search_terms, location, limit
                )
                if dataset_items:
                    break
            except Exception as exc:
                last_error = exc
                continue

        if not dataset_items and last_error:
            raise last_error

        leads_data = []
        for item in dataset_items[:limit]:
            if item.get("permanentlyClosed") or item.get("temporarilyClosed"):
                continue
            lead_data = self._map_apify_item(item, location)
            lead_data = normalize_website_field(lead_data)
            company = lead_data.get("company_name")
            if company and company != "Unknown":
                leads_data.append(lead_data)
        return leads_data

    def _normalize_location(self, location: str) -> str:
        from app.utils.scrape_defaults import normalize_location_alias

        return normalize_location_alias(location)

    def _run_maps_actor(
        self,
        client: ApifyClient,
        actor_id: str,
        search_terms: list[str],
        location: str,
        limit: int,
    ) -> list[dict]:
        run_input = {
            "searchStringsArray": search_terms,
            "locationQuery": location,
            "maxCrawledPlacesPerSearch": limit,
            "maxCrawledPlaces": limit,
            "language": "en",
            "skipClosedPlaces": True,
            "scrapeReviewerName": False,
            "scrapeReviewerId": False,
            "scrapeReviewId": False,
            "scrapeReviewUrl": False,
            "scrapeResponseFromOwnerText": False,
        }
        return self._run_actor_raw(client, actor_id, run_input)

    def _run_actor_raw(
        self, client: ApifyClient, actor_id: str, run_input: dict
    ) -> list[dict]:
        run = client.actor(actor_id).call(run_input=run_input)
        dataset_id = (
            run["defaultDatasetId"]
            if isinstance(run, dict)
            else run.default_dataset_id
        )
        return list(client.dataset(dataset_id).iterate_items())

    def _map_apify_item(self, item: dict, fallback_location: str) -> dict:
        address = item.get("address") or item.get("street") or ""
        city = item.get("city") or item.get("neighborhood") or self._extract_city(address)
        country = item.get("country") or item.get("countryCode") or ""
        if not country and "," in fallback_location:
            country = fallback_location.split(",")[-1].strip()

        categories = item.get("categories") or []
        industry = item.get("categoryName") or (
            categories[0] if categories else None
        )
        category = ", ".join(categories) if categories else industry
        full_address = item.get("address") or item.get("street") or ""
        postal_code = (
            item.get("postalCode")
            or item.get("zip")
            or item.get("zipCode")
            or self._extract_postal_code(full_address)
        )

        website = item.get("website") or item.get("websiteUrl")
        raw_url = item.get("url")
        if not website and raw_url and not is_google_maps_url(raw_url):
            website = raw_url

        raw_phone = item.get("phone") or item.get("phoneUnformatted")
        formatted_phone = None
        if raw_phone:
            from app.utils.contact_utils import format_contact_phone

            phone_country = country or (
                fallback_location.split(",")[-1].strip() if "," in fallback_location else None
            )
            formatted_phone = format_contact_phone(str(raw_phone), phone_country)
            if formatted_phone:
                digits = re.sub(r"\D", "", formatted_phone)
                if len(digits) < 10:
                    formatted_phone = None

        mapped = {
            "company_name": item.get("title")
            or item.get("name")
            or item.get("subTitle")
            or item.get("companyName")
            or "Unknown",
            "contact_name": item.get("contactName") or item.get("ownerName"),
            "phone": formatted_phone,
            "email": item.get("email"),
            "website": website,
            "linkedin_url": item.get("linkedin"),
            "facebook_url": item.get("facebook"),
            "instagram_url": item.get("instagram"),
            "address": full_address or None,
            "postal_code": postal_code,
            "category": category,
            "city": city or item.get("state"),
            "country": country,
            "industry": industry,
            "notes": (
                item.get("description")
                or item.get("categoryName")
                or (", ".join(categories) if categories else None)
            ),
            "source": "apify",
            "status": LeadStatus.new,
        }
        from app.services.intelligence.maps_enrichment import enrich_maps_lead

        return enrich_maps_lead(item, mapped)

    def _extract_postal_code(self, address: str) -> str | None:
        if not address:
            return None
        match = re.search(r"\b(\d{4,6})(?:-\d{4})?\b", address)
        return match.group(1) if match else None

    def _extract_city(self, address: str) -> str | None:
        if not address:
            return None
        parts = [part.strip() for part in address.split(",")]
        if len(parts) >= 2:
            return parts[-2]
        return parts[0] if parts else None
