import logging
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import nullcontext
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.scraper.metrics import ScrapeMetrics
from app.scraper.utils.workers import compute_parallel_workers
from app.scrapers.fetcher import PageFetcher
from app.scrapers.playwright_pool import playwright_session
from app.utils.contact_utils import (
    extract_instagram_urls,
    extract_linkedin_urls,
    format_contact_phone,
    is_valid_email,
    is_whatsapp_ready,
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
        metrics: ScrapeMetrics | None = None,
    ) -> list[dict]:
        if not leads_data:
            return []

        settings = get_settings()
        fast = bool(settings.SCRAPER_FAST_MODE)
        total = len(leads_data)
        enriched: list[dict | None] = [None] * total

        # Skip deep enrich when contact already present — biggest win at ~60%
        need_indices: list[int] = []
        for index, item in enumerate(leads_data):
            if self._already_has_contacts(item):
                enriched[index] = sanitize_lead_contacts(
                    dict(item), search_location=item.get("country")
                )
            else:
                need_indices.append(index)

        done = total - len(need_indices)
        if on_progress:
            on_progress(done, total)

        if not need_indices:
            return [item for item in enriched if item is not None]

        # Fast mode: enrich only a small slice — rest keep discovery contacts
        if fast and len(need_indices) > 8:
            for index in need_indices[8:]:
                enriched[index] = sanitize_lead_contacts(
                    dict(leads_data[index]),
                    search_location=leads_data[index].get("country"),
                )
                done += 1
            need_indices = need_indices[:8]
            if on_progress:
                on_progress(done, total)

        workers = min(
            6 if fast else settings.SCRAPER_MAX_WORKERS,
            compute_parallel_workers(len(need_indices), max_workers=settings.SCRAPER_MAX_WORKERS),
        )
        # Hard wall clock so enrich never stalls the scrape at ~60%
        budget = 18.0 if fast else 60.0
        deadline = time.monotonic() + budget
        logger.info(
            "Enriching %s/%s leads · workers=%s · budget=%.0fs · fast=%s",
            len(need_indices),
            total,
            workers,
            budget,
            fast,
        )
        if metrics is not None:
            metrics.set("active_workers", workers)
            metrics.set("queue_size", len(need_indices))

        pw_cm = nullcontext() if fast else playwright_session()
        with pw_cm:
            executor = ThreadPoolExecutor(max_workers=workers)
            futures = {
                executor.submit(
                    self.enrich_lead, leads_data[index], fast=fast, metrics=metrics
                ): index
                for index in need_indices
            }
            pending = set(futures.keys())
            try:
                while pending and time.monotonic() < deadline:
                    finished, pending = wait(pending, timeout=0.4, return_when=FIRST_COMPLETED)
                    for future in finished:
                        index = futures[future]
                        try:
                            enriched[index] = future.result(timeout=0)
                        except Exception as exc:
                            logger.debug("Enrich failed for lead %s: %s", index, exc)
                            enriched[index] = sanitize_lead_contacts(
                                dict(leads_data[index]),
                                search_location=leads_data[index].get("country"),
                            )
                        done += 1
                        if on_progress:
                            on_progress(done, total)
                        if metrics is not None:
                            metrics.set("queue_size", len(pending))
                            metrics.set(
                                "active_workers",
                                min(workers, max(0, len(pending))),
                            )
            finally:
                for fut in pending:
                    fut.cancel()
                    index = futures[fut]
                    if enriched[index] is None:
                        enriched[index] = sanitize_lead_contacts(
                            dict(leads_data[index]),
                            search_location=leads_data[index].get("country"),
                        )
                        done += 1
                        if on_progress:
                            on_progress(min(done, total), total)
                executor.shutdown(wait=False, cancel_futures=True)
                if metrics is not None:
                    metrics.set("active_workers", 0)
                    metrics.set("queue_size", 0)

        return [item for item in enriched if item is not None]

    @staticmethod
    def _already_has_contacts(lead: dict) -> bool:
        has_email = bool(lead.get("email") and is_valid_email(str(lead["email"])))
        has_phone = bool(lead.get("phone") and len(str(lead["phone"]).strip()) >= 7)
        # One solid contact is enough — skip slow re-crawl of contact pages
        return has_email or has_phone

    def enrich_lead(
        self,
        lead_data: dict,
        *,
        fast: bool | None = None,
        metrics: ScrapeMetrics | None = None,
    ) -> dict:
        settings = get_settings()
        if fast is None:
            fast = bool(settings.SCRAPER_FAST_MODE)

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

        if self._already_has_contacts(enriched):
            enriched = self._finalize_contacts(enriched)
            self._append_enrichment_tags(enriched)
            return enriched

        if website:
            pages_html: list[str] = []
            homepage = self._fetch_page_text(website, fast=fast, metrics=metrics)
            if homepage:
                pages_html.append(homepage)

            max_extra = 1 if fast else 4
            for contact_url in self._contact_page_urls(website, homepage or "", max_urls=max_extra):
                if self._already_has_contacts(enriched):
                    break
                contact_html = self._fetch_page_text(contact_url, fast=fast, metrics=metrics)
                if contact_html:
                    pages_html.append(contact_html)

            if pages_html:
                self._extract_contacts_from_pages(enriched, pages_html, country, website)
        elif enriched.get("facebook_url") and not fast:
            fb_html = self._fetch_page_text(enriched["facebook_url"], fast=fast, metrics=metrics)
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

    def _contact_page_urls(
        self, website: str, homepage_html: str, *, max_urls: int = 5
    ) -> list[str]:
        base = website if website.startswith("http") else f"https://{website}"
        host = urlparse(base).netloc.lower()
        found: list[str] = []
        cap = max(1, max_urls)

        if homepage_html:
            soup = BeautifulSoup(homepage_html, "lxml")
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"].strip().lower()
                if any(path.strip("/") in href for path in CONTACT_PATHS):
                    full = urljoin(base, anchor["href"])
                    if urlparse(full).netloc.lower() == host and full not in found:
                        found.append(full)
                if len(found) >= cap:
                    break

        for path in CONTACT_PATHS[:3]:
            url = urljoin(base, path)
            if url not in found:
                found.append(url)
            if len(found) >= cap:
                break

        return found[:cap]

    def _fetch_page_text(
        self,
        website: str,
        *,
        fast: bool = False,
        metrics: ScrapeMetrics | None = None,
    ) -> str:
        html, _ = PageFetcher(
            timeout=3.5 if fast else None,
            use_playwright=False if fast else None,
            metrics=metrics,
        ).fetch(website)
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
