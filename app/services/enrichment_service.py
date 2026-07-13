import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.scraper.utils.workers import compute_parallel_workers
from app.scrapers.fetcher import PageFetcher
from app.scrapers.playwright_pool import playwright_session
from app.utils.contact_utils import (
    extract_instagram_urls,
    extract_linkedin_urls,
    format_contact_phone,
    is_valid_email,
    is_whatsapp_ready,
    pick_best_email,
    pick_best_phone,
    score_email,
)
from app.utils.contact_verifier import verify_email_deliverability
from app.utils.lead_contacts import merge_contact_fields, sanitize_lead_contacts

logger = logging.getLogger(__name__)

CONTACT_PATHS = (
    "/contact",
    "/contact-us",
    "/contactus",
    "/about",
    "/about-us",
    "/get-in-touch",
    "/reach-us",
    "/impressum",
    "/kontakt",
)


class EnrichmentService:
    def enrich_leads_batch(
        self,
        leads_data: list[dict],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[dict]:
        if not leads_data:
            return []

        settings = get_settings()
        workers = compute_parallel_workers(len(leads_data), max_workers=settings.SCRAPER_MAX_WORKERS)
        total = len(leads_data)
        enriched: list[dict | None] = [None] * total

        with playwright_session():
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(self.enrich_lead, item): index
                    for index, item in enumerate(leads_data)
                }
                done = 0
                for future in as_completed(futures):
                    index = futures[future]
                    try:
                        enriched[index] = future.result()
                    except Exception as exc:
                        logger.debug("Enrich failed for lead %s: %s", index, exc)
                        enriched[index] = sanitize_lead_contacts(
                            dict(leads_data[index]),
                            search_location=leads_data[index].get("country"),
                        )
                    done += 1
                    if on_progress:
                        on_progress(done, total)

        return [item for item in enriched if item is not None]

    def enrich_lead(self, lead_data: dict) -> dict:
        country = lead_data.get("country")
        enriched = sanitize_lead_contacts(dict(lead_data), search_location=country)
        website = enriched.get("website")

        snippet_text = " ".join(
            part
            for part in [enriched.get("company_name"), enriched.get("notes")]
            if part
        )
        if snippet_text:
            merge_contact_fields(enriched, snippet_text, country)

        if website:
            pages_html: list[str] = []
            homepage = self._fetch_page_text(website)
            if homepage:
                pages_html.append(homepage)

            for contact_url in self._contact_page_urls(website, homepage or ""):
                contact_html = self._fetch_page_text(contact_url)
                if contact_html:
                    pages_html.append(contact_html)

            self._extract_contacts_from_pages(enriched, pages_html, country, website)
        elif enriched.get("facebook_url"):
            fb_html = self._fetch_page_text(enriched["facebook_url"])
            if fb_html:
                merge_contact_fields(enriched, fb_html, country)
                self._extract_contacts_from_pages(
                    enriched, [fb_html], country, enriched["facebook_url"]
                )

        enriched = self._finalize_contacts(enriched)
        self._append_enrichment_tags(enriched)
        return enriched

    def _finalize_contacts(self, lead_data: dict) -> dict:
        country = lead_data.get("country")
        website = lead_data.get("website")

        email = lead_data.get("email")
        if email:
            email = email.strip().lower()
            if not is_valid_email(email):
                email = None
            elif not verify_email_deliverability(email, website):
                email = None
            lead_data["email"] = email

        from app.utils.contact_utils import _effective_country_for_phone

        phone_country = _effective_country_for_phone(lead_data.get("phone"), country) or country
        normalized = format_contact_phone(lead_data.get("phone"), phone_country)
        lead_data["phone"] = normalized

        location_hint = lead_data.get("country")
        return sanitize_lead_contacts(lead_data, search_location=location_hint)

    def _extract_contacts_from_pages(
        self,
        enriched: dict,
        pages_html: list[str],
        country: str | None,
        base_url: str,
    ) -> None:
        from app.scrapers.parser import extract_contacts_from_html
        from app.utils.phone_confidence import aggregate_phone_hits
        from app.utils.phone_extract import extract_phone_hits_from_html

        phone_country = country
        all_hits = []
        for page_html in pages_html:
            all_hits.extend(extract_phone_hits_from_html(page_html, phone_country))
            contacts = extract_contacts_from_html(page_html, base_url, phone_country, None)
            if contacts.get("country"):
                phone_country = contacts["country"]
            if contacts.get("email") and not enriched.get("email"):
                enriched["email"] = contacts["email"]
            self._merge_social_links(enriched, page_html)

        verified = aggregate_phone_hits(all_hits, phone_country)
        if verified:
            enriched["phone"] = verified

    def _append_enrichment_tags(self, lead_data: dict) -> None:
        tags = []
        if lead_data.get("email") and is_valid_email(lead_data["email"]):
            tags.append("verified-email")
        if lead_data.get("phone") and is_whatsapp_ready(lead_data["phone"], lead_data.get("country")):
            tags.append("verified-whatsapp")
        if lead_data.get("linkedin_url"):
            tags.append("linkedin")
        if lead_data.get("website"):
            tags.append("has-website")
        else:
            tags.append("no-website")

        if tags:
            note = lead_data.get("notes") or ""
            tag_line = f"[Verified: {', '.join(tags)}]"
            lead_data["notes"] = f"{note}\n{tag_line}".strip() if note else tag_line

    def _contact_page_urls(self, website: str, homepage_html: str) -> list[str]:
        base = website if website.startswith("http") else f"https://{website}"
        host = urlparse(base).netloc.lower()
        found: list[str] = []

        if homepage_html:
            soup = BeautifulSoup(homepage_html, "lxml")
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"].strip().lower()
                if any(path.strip("/") in href for path in CONTACT_PATHS):
                    full = urljoin(base, anchor["href"])
                    if urlparse(full).netloc.lower() == host and full not in found:
                        found.append(full)
                if len(found) >= 4:
                    break

        for path in CONTACT_PATHS:
            url = urljoin(base, path)
            if url not in found:
                found.append(url)
            if len(found) >= 5:
                break

        return found[:5]

    def _fetch_page_text(self, website: str) -> str:
        html, _ = PageFetcher().fetch(website)
        return html or ""

    def _merge_social_links(self, lead_data: dict, page_text: str) -> None:
        if not lead_data.get("linkedin_url"):
            linkedin_urls = extract_linkedin_urls(page_text)
            if linkedin_urls:
                lead_data["linkedin_url"] = linkedin_urls[0]

        if not lead_data.get("instagram_url"):
            instagram_urls = extract_instagram_urls(page_text)
            if instagram_urls:
                lead_data["instagram_url"] = instagram_urls[0]
