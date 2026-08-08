import logging
from typing import Callable
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.campaign import MessageType
from app.models.lead import Lead
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.cv_repository import CVRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.message_repository import MessageRepository
from app.scraper.api.dashboard import build_scrape_dashboard
from app.scraper.metrics import ScrapeMetrics
from app.scraper.validators.quality import apply_quality_to_lead
from app.schemas.common import ScraperStartRequest, ScraperStartResponse, WhatsAppLeadPreview
from app.services.apify_service import ApifyService
from app.services.enrichment_service import EnrichmentService
from app.services.groq_service import GroqService
from app.services.meta_ads_service import MetaAdsService
from app.utils.contact_utils import build_whatsapp_link, is_valid_email, is_whatsapp_ready
from app.utils.lead_contacts import sanitize_lead_contacts
from app.utils.scrape_sources import ScrapeSourceMode, dedupe_leads, derive_maps_search_params
from app.utils.scrape_context import tag_leads_with_scrape_context
from app.utils.scrape_defaults import normalize_location_alias
from app.scraper.utils.workers import compute_source_workers
from app.utils.website_utils import WebsiteFilter, apply_website_filter, has_real_website

ProgressCallback = Callable[[int, str, str], None]
LogCallback = Callable[[str, str, str], None]  # level, stage, text

logger = logging.getLogger(__name__)


class AllInOneScraperService:
    def __init__(self, db: Session):
        self.lead_repository = LeadRepository(db)
        self.cv_repository = CVRepository(db)
        self.campaign_repository = CampaignRepository(db)
        self.message_repository = MessageRepository(db)
        self.apify_service = ApifyService(self.lead_repository)
        self.enrichment_service = EnrichmentService()
        self.meta_ads_service = MetaAdsService()
        self.db = db
        from app.services.api_key_rotation_service import ApiKeyRotationService

        self.rotation = ApiKeyRotationService(db)
        self.groq_service = GroqService(db)

    def run(
        self,
        user: User,
        data: ScraperStartRequest,
        on_progress: ProgressCallback | None = None,
        on_log: LogCallback | None = None,
        *,
        background: bool = False,
        job_id: str | None = None,
        metrics: ScrapeMetrics | None = None,
    ) -> ScraperStartResponse:
        def log(level: str, stage: str, text: str) -> None:
            if on_log:
                on_log(level, stage, text)

        def prog(percent: int, stage: str, message: str) -> None:
            if on_progress:
                on_progress(percent, stage, message)
            log("info", stage, message)

        prog(5, "init", "Preparing scraper...")
        source_label = getattr(data.scrape_source, "value", str(data.scrape_source))
        log("info", "init", f"Source: {source_label} · limit {data.limit}")
        if data.search_query and data.search_query.strip():
            log("info", "init", f"Query: {data.search_query.strip()}")
        if data.keyword and data.keyword.strip():
            log("info", "init", f"Keyword: {data.keyword.strip()}")
        if data.location and data.location.strip():
            log("info", "init", f"Location: {data.location.strip()}")

        if background:
            data = data.model_copy(
                update={
                    "website_filter": WebsiteFilter.all,
                    "only_verified_contacts": False,
                }
            )
            log("info", "init", "Background mode — collecting all leads (no filters)")

        self.groq_service.user_id = user.id
        settings = get_settings()
        keyword = data.keyword.strip()
        location = normalize_location_alias(self.apify_service._normalize_location(data.location.strip()))
        maps_keyword, maps_location = derive_maps_search_params(
            keyword, data.location, data.search_query
        )
        needs_maps = data.scrape_source in (ScrapeSourceMode.all, ScrapeSourceMode.google_maps)
        needs_web = data.scrape_source in (ScrapeSourceMode.all, ScrapeSourceMode.google_search)
        needs_meta_only = data.scrape_source == ScrapeSourceMode.meta_ads
        needs_meta = needs_meta_only or (
            data.include_meta_ads and data.scrape_source == ScrapeSourceMode.all
        )
        per_source_limit = (
            data.limit if data.scrape_source != ScrapeSourceMode.all else max(data.limit // 2, 10)
        )

        # Release SQLite transaction before long network I/O so login/API stay responsive
        try:
            if self.db.in_transaction():
                self.db.commit()
        except Exception:
            self.db.rollback()

        maps_leads: list[dict] = []
        search_leads: list[dict] = []
        meta_leads: list[dict] = []
        errors: list[str] = []
        scrape_metrics = metrics or ScrapeMetrics()
        if job_id:
            from app.services.scraper_job_store import scraper_job_store

            scraper_job_store.bind_metrics(job_id, scrape_metrics)

        def scrape_maps(
            maps_kw: str | None = None,
            maps_loc: str | None = None,
            result_limit: int | None = None,
        ) -> list[dict]:
            from app.services.scraper_job_store import scraper_job_store as _store

            mk = maps_kw or keyword
            ml = maps_loc or location
            lim = result_limit if result_limit is not None else per_source_limit
            job_control = (lambda: _store.should_abort(job_id)) if job_id else None
            no_site = data.website_filter == WebsiteFilter.without_website
            # Local Playwright only — https://github.com/kevmaindev/Googles-Maps-Scraper
            return self.apify_service.scrape_maps_playwright_local(
                mk,
                ml,
                lim,
                job_control=job_control,
                require_no_website=no_site,
            )

        def scrape_web() -> list[dict]:
            from app.services.scraper_job_store import scraper_job_store

            job_control = None
            if job_id:
                job_control = lambda: scraper_job_store.should_abort(job_id)
            return self.apify_service.web_search_service.search_leads(
                data.keyword,
                data.location,
                per_source_limit,
                search_query=data.search_query,
                metrics=scrape_metrics,
                website_filter=data.website_filter,
                job_control=job_control,
                job_id=job_id,
            )

        def scrape_meta() -> list[dict]:
            return self.meta_ads_service.search_leads(
                data.keyword,
                data.location,
                per_source_limit,
                search_query=data.search_query,
                user_id=user.id,
                db=self.db,
            )

        if needs_meta_only:
            prog(20, "meta_ads", "Searching Meta Ad Library (Facebook/Instagram ads)...")
            try:
                meta_leads = scrape_meta()
                prog(55, "meta_ads", f"Meta Ads: found {len(meta_leads)} advertisers")
            except Exception as exc:
                errors.append(f"Meta Ads: {exc}")
                prog(55, "meta_ads", f"Meta Ads failed: {exc}")
        elif needs_maps and needs_web:
            from concurrent.futures import wait, FIRST_COMPLETED
            from app.services.scraper_job_store import scraper_job_store as _job_store

            if job_id and _job_store.is_cancelled(job_id):
                prog(100, "cancelled", "Stopped")
                return ScraperStartResponse(success=True, count=0, message="Stopped")

            # Avoid dual Chromium OOM on Postgres/Railway (Maps Target crashed)
            db_url = (settings.DATABASE_URL or "").lower()
            serialize = (not settings.SCRAPER_PARALLEL_SOURCES) or ("postgres" in db_url)
            if serialize:
                # Internet first so UI moves and leads arrive even if Maps is slow/blocked
                internet_first = bool(settings.SCRAPER_INTERNET_BEFORE_MAPS) or (
                    "postgres" in db_url
                )
                if internet_first:
                    prog(10, "web_search", "Searching the internet...")
                    try:
                        search_leads = scrape_web()
                        prog(35, "web_search", f"Internet: found {len(search_leads)} results")
                    except Exception as exc:
                        errors.append(f"Internet: {exc}")
                        prog(35, "web_search", f"Internet failed: {exc}")
                    if job_id and _job_store.is_cancelled(job_id):
                        prog(100, "cancelled", "Stopped")
                        return ScraperStartResponse(success=True, count=0, message="Stopped")
                    prog(40, "google_maps", "Finding local businesses on Maps...")
                    try:
                        maps_leads = scrape_maps()
                        prog(55, "google_maps", f"Google Maps: found {len(maps_leads)} businesses")
                    except Exception as exc:
                        errors.append(f"Google Maps: {exc}")
                        prog(55, "google_maps", f"Google Maps failed: {exc}")
                else:
                    prog(10, "google_maps", "Finding local businesses...")
                    try:
                        maps_leads = scrape_maps()
                        prog(30, "google_maps", f"Google Maps: found {len(maps_leads)} businesses")
                    except Exception as exc:
                        errors.append(f"Google Maps: {exc}")
                        prog(30, "google_maps", f"Google Maps failed: {exc}")
                    if job_id and _job_store.is_cancelled(job_id):
                        prog(100, "cancelled", "Stopped")
                        return ScraperStartResponse(success=True, count=0, message="Stopped")
                    prog(35, "web_search", "Searching the internet...")
                    try:
                        search_leads = scrape_web()
                        prog(50, "web_search", f"Internet: found {len(search_leads)} results")
                    except Exception as exc:
                        errors.append(f"Internet: {exc}")
                        prog(50, "web_search", f"Internet failed: {exc}")
                if needs_meta:
                    if job_id and _job_store.is_cancelled(job_id):
                        prog(100, "cancelled", "Stopped")
                        return ScraperStartResponse(success=True, count=0, message="Stopped")
                    prog(58, "meta_ads", "Searching Meta Ad Library...")
                    try:
                        meta_leads = scrape_meta()
                        prog(62, "meta_ads", f"Meta Ads: found {len(meta_leads)} advertisers")
                    except Exception as exc:
                        errors.append(f"Meta Ads: {exc}")
                        prog(62, "meta_ads", f"Meta Ads failed: {exc}")
            else:
                prog(10, "parallel", "Google Maps + Internet + Meta Ads (parallel)...")
                parallel_workers = compute_source_workers(3 if needs_meta else 2)
                scrape_metrics.set("active_workers", parallel_workers)
                scrape_metrics.set("queue_size", 3 if needs_meta else 2)
                with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                    maps_future = executor.submit(scrape_maps)
                    web_future = executor.submit(scrape_web)
                    meta_future = executor.submit(scrape_meta) if needs_meta else None
                    pending = {maps_future, web_future}
                    if meta_future:
                        pending.add(meta_future)

                    while pending:
                        if job_id and _job_store.is_cancelled(job_id):
                            for fut in pending:
                                fut.cancel()
                            prog(100, "cancelled", "Stopped")
                            return ScraperStartResponse(success=True, count=0, message="Stopped")

                        done, pending = wait(pending, timeout=0.4, return_when=FIRST_COMPLETED)
                        scrape_metrics.set("queue_size", len(pending))
                        scrape_metrics.set(
                            "active_workers",
                            min(parallel_workers, max(0, len(pending))),
                        )
                        for future in done:
                            try:
                                result = future.result()
                            except Exception as exc:
                                if future is maps_future:
                                    errors.append(f"Google Maps: {exc}")
                                    prog(30, "google_maps", f"Google Maps failed: {exc}")
                                elif future is web_future:
                                    errors.append(f"Internet: {exc}")
                                    prog(45, "web_search", f"Internet failed: {exc}")
                                else:
                                    errors.append(f"Meta Ads: {exc}")
                                    prog(55, "meta_ads", f"Meta Ads failed: {exc}")
                                continue
                            if future is maps_future:
                                maps_leads = result
                                prog(30, "google_maps", f"Google Maps: found {len(maps_leads)} businesses")
                            elif future is web_future:
                                search_leads = result
                                prog(45, "web_search", f"Internet: found {len(search_leads)} results")
                            else:
                                meta_leads = result
                                prog(55, "meta_ads", f"Meta Ads: found {len(meta_leads)} advertisers")
                scrape_metrics.set("active_workers", 0)
                scrape_metrics.set("queue_size", 0)
        elif needs_maps:
            prog(10, "google_maps", "Finding local businesses...")
            try:
                maps_leads = scrape_maps()
                prog(40, "google_maps", f"Found {len(maps_leads)} businesses with phone")
            except Exception as exc:
                errors.append(f"Google Maps: {exc}")
                prog(40, "google_maps", "Could not finish business search")
            # Maps-only often hangs/blocked on Railway — fall back to Internet so scrape still works
            if not maps_leads:
                from app.services.scraper_job_store import scraper_job_store as _job_store

                if not (job_id and _job_store.is_cancelled(job_id)):
                    prog(45, "web_search", "Maps empty — searching the internet...")
                    try:
                        search_leads = scrape_web()
                        prog(55, "web_search", f"Internet: found {len(search_leads)} results")
                    except Exception as exc:
                        errors.append(f"Internet: {exc}")
                        prog(55, "web_search", f"Internet failed: {exc}")
        elif needs_web:
            from app.services.scraper_job_store import scraper_job_store as _job_store

            if job_id and _job_store.is_cancelled(job_id):
                prog(100, "cancelled", "Stopped")
                return ScraperStartResponse(success=True, count=0, message="Stopped")

            prog(20, "google_maps", "Finding local businesses...")
            try:
                maps_leads = scrape_maps(
                    maps_keyword or keyword,
                    maps_location or location,
                    per_source_limit,
                )
                prog(
                    45,
                    "google_maps",
                    f"Found {len(maps_leads)} businesses with phone",
                )
            except Exception as exc:
                errors.append(f"Google Maps: {exc}")
                prog(45, "google_maps", "Could not finish business search")

            # Supplement with web search only when Maps is thin
            if (
                len(maps_leads) < max(2, per_source_limit // 3)
                and not (job_id and _job_store.is_cancelled(job_id))
            ):
                prog(48, "web_search", "Supplementing with Internet search...")
                web_ex = ThreadPoolExecutor(max_workers=1)
                try:
                    web_timeout = max(
                        40.0, float(settings.SCRAPER_INTERNET_MAX_SECONDS or 60.0)
                    )
                    web_fut = web_ex.submit(scrape_web)
                    try:
                        search_leads = web_fut.result(timeout=web_timeout)
                        prog(
                            55,
                            "web_search",
                            f"Internet: found {len(search_leads)} results",
                        )
                    except TimeoutError:
                        prog(55, "web_search", f"Internet supplement timed out")
                        search_leads = []
                except Exception as exc:
                    errors.append(f"Internet: {exc}")
                    prog(55, "web_search", f"Internet failed: {exc}")
                finally:
                    web_ex.shutdown(wait=False, cancel_futures=True)

            if needs_meta:
                prog(56, "meta_ads", "Searching Meta Ad Library...")
                try:
                    meta_leads = scrape_meta()
                    prog(58, "meta_ads", f"Meta Ads: found {len(meta_leads)} advertisers")
                except Exception as exc:
                    errors.append(f"Meta Ads: {exc}")
                    prog(58, "meta_ads", f"Meta Ads failed: {exc}")

        if not maps_leads and not search_leads and not meta_leads:
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Scraping failed. {'; '.join(errors)}",
                )
            no_data_label = (data.search_query or keyword or "your query").strip()
            loc_label = data.location.strip() or maps_location
            return ScraperStartResponse(
                success=True,
                count=0,
                message=(
                    f"No leads found for '{no_data_label}'"
                    + (f" in '{loc_label}'" if loc_label else "")
                    + ". Try a broader search query or different location."
                ),
            )

        prog(58, "merge", "Merging and removing duplicates...")
        leads_data = dedupe_leads(maps_leads + search_leads + meta_leads)[: data.limit]
        leads_discovered = len(leads_data)
        log("info", "merge", f"Merged {leads_discovered} unique lead(s)")
        for lead in leads_data[:25]:
            name = (lead.get("company_name") or "Unknown").strip()
            phone = lead.get("phone") or "no phone"
            src = lead.get("source") or "web"
            log("lead", "merge", f"→ {name} · {phone} · {src}")
        if leads_discovered > 25:
            log("info", "merge", f"… and {leads_discovered - 25} more")
        leads_data = [apply_quality_to_lead(lead) for lead in leads_data]
        for lead in leads_data:
            from app.scraper.validators.quality import QUALITY_HIGH, QUALITY_LOW, QUALITY_MEDIUM
            from app.utils.contact_utils import is_valid_email

            tier = lead.get("quality_tier")
            if tier == QUALITY_HIGH:
                scrape_metrics.inc("high_quality")
            elif tier == QUALITY_MEDIUM:
                scrape_metrics.inc("medium_quality")
            elif tier == QUALITY_LOW:
                scrape_metrics.inc("low_quality")
            if lead.get("email") and is_valid_email(lead.get("email")):
                scrape_metrics.inc("valid_emails")
            if lead.get("phone"):
                scrape_metrics.inc("valid_phones")
            if lead.get("whatsapp_ready"):
                scrape_metrics.inc("whatsapp_ready")
        maps_count, search_count, meta_count = self.apify_service.count_by_source(leads_data)

        if data.enrich_contacts:
            def enrich_progress(done: int, total_count: int) -> None:
                # Map enrich into 58→78 so UI doesn't sit frozen at ~60%
                pct = 58 + int(20 * done / max(total_count, 1))
                prog(
                    min(78, pct),
                    "enrich",
                    f"Enriching contacts {done}/{total_count}...",
                )

            prog(58, "enrich", f"Enriching contacts (0/{len(leads_data)})...")
            leads_data = self.enrichment_service.enrich_leads_batch(
                leads_data, on_progress=enrich_progress, metrics=scrape_metrics
            )
        else:
            leads_data = [
                sanitize_lead_contacts(lead, search_location=location or None)
                for lead in leads_data
            ]

        filtered_website = 0
        if not background:
            prog(78, "filter", "Applying website filter...")
            before_website = len(leads_data)
            preferred = apply_website_filter(leads_data, data.website_filter)
            filtered_website = before_website - len(preferred)

            # Soft-fill: "without website" is rare on Maps — top up with phone leads
            if (
                data.website_filter == WebsiteFilter.without_website
                and len(preferred) < max(3, min(int(data.limit or 10), 8))
                and needs_maps
            ):
                prog(
                    80,
                    "google_maps",
                    "Few no-website businesses — topping up with phone leads…",
                )
                try:
                    from app.services.scraper_job_store import scraper_job_store as _job_store

                    job_control = (
                        (lambda: _job_store.should_abort(job_id)) if job_id else None
                    )
                    topup = self.apify_service.scrape_maps_playwright_local(
                        maps_keyword or keyword,
                        maps_location or location,
                        max(int(data.limit or 10), 12),
                        job_control=job_control,
                        require_no_website=False,
                    )
                    if data.enrich_contacts:
                        topup = self.enrichment_service.enrich_leads_batch(topup)
                    else:
                        topup = [
                            sanitize_lead_contacts(lead, search_location=location or None)
                            for lead in topup
                        ]
                    merged = dedupe_leads(list(preferred) + list(topup))
                    no_site = [
                        lead for lead in merged if not has_real_website(lead.get("website"))
                    ]
                    with_site = [
                        lead
                        for lead in merged
                        if has_real_website(lead.get("website"))
                        and (
                            (lead.get("phone") and str(lead.get("phone")).strip())
                            or (lead.get("email") and is_valid_email(lead.get("email")))
                        )
                    ]
                    leads_data = (no_site + with_site)[: data.limit]
                    leads_discovered = max(leads_discovered, len(merged))
                    filtered_website = max(0, before_website - len(no_site))
                    log(
                        "info",
                        "filter",
                        f"Kept {len(no_site)} without website + "
                        f"{max(0, len(leads_data) - len(no_site))} phone fill",
                    )
                except Exception as exc:
                    leads_data = preferred
                    errors.append(f"Maps top-up: {exc}")
                    log("warn", "filter", f"Top-up failed: {exc}")
            else:
                leads_data = preferred
        else:
            prog(78, "filter", "Background mode — keeping all discovered leads")

        if not leads_data:
            filter_label = data.website_filter.value.replace("_", " ")
            hint = (
                " Use Google Maps source with a local keyword (restaurant, salon) and your city."
                if data.website_filter == WebsiteFilter.without_website
                else " Try a broader keyword or increase max results."
            )
            return ScraperStartResponse(
                success=True,
                count=0,
                leads_discovered=leads_discovered,
                filtered_website=filtered_website,
                message=(
                    f"Found {leads_discovered} lead(s) but none without website ({filter_label}) for "
                    f"'{keyword or data.search_query}' in '{data.location or maps_location}'."
                    f"{hint}"
                ),
            )

        leads_data = [apply_quality_to_lead(lead) for lead in leads_data]

        # Without-website mode: prefer contactable leads (phone/email) — that's the product goal
        if data.website_filter == WebsiteFilter.without_website:
            with_contact = [
                lead
                for lead in leads_data
                if (lead.get("phone") and str(lead.get("phone")).strip())
                or (lead.get("email") and is_valid_email(lead.get("email")))
            ]
            if with_contact:
                leads_data = with_contact
                log(
                    "info",
                    "filter",
                    f"Kept {len(leads_data)} without-website lead(s) that have phone/email",
                )

        before_verified = len(leads_data)
        filtered_unverified = 0
        if data.only_verified_contacts:
            verified_leads = [
                lead
                for lead in leads_data
                if (lead.get("email") and is_valid_email(lead.get("email")))
                or (lead.get("phone") and is_whatsapp_ready(lead.get("phone"), lead.get("country")))
            ]
            filtered_unverified = before_verified - len(verified_leads)
            leads_data = verified_leads

        if not leads_data:
            return ScraperStartResponse(
                success=True,
                count=0,
                leads_discovered=leads_discovered,
                filtered_unverified=filtered_unverified,
                filtered_website=filtered_website,
                message=(
                    f"Found {leads_discovered} lead(s) but {filtered_unverified} had no verified "
                    "email or WhatsApp number. Turn off 'Verified contacts only' to save more leads."
                ),
            )

        prog(88, "save", f"Saving {len(leads_data)} leads to database...")
        scrape_metrics.inc("leads_saved", len(leads_data))
        from app.services.lead_service import LeadService

        leads_data = tag_leads_with_scrape_context(leads_data, data, background=background)
        lead_service = LeadService(self.db)
        leads, imported, skipped_dupes, intel_stats = lead_service.save_scraped_leads(
            user.id, leads_data, search_location=data.location or maps_location
        )
        hot = intel_stats.get("hot_leads", 0) if intel_stats else 0
        log(
            "success",
            "save",
            f"Saved {imported} lead(s) · skipped {skipped_dupes} duplicate(s)"
            + (f" · {hot} HOT" if hot else ""),
        )
        for lead in leads[:20]:
            tier = getattr(lead, "intent_tier", None) or ""
            tag = f" [{tier.upper()}]" if tier else ""
            log("success", "save", f"✓ {lead.company_name} · {lead.phone or '—'}{tag}")

        if not leads:
            return ScraperStartResponse(
                success=True,
                count=0,
                leads_discovered=leads_discovered,
                filtered_unverified=filtered_unverified,
                filtered_website=filtered_website,
                message=(
                    f"Found {leads_discovered} lead(s) but all {skipped_dupes} already exist in your "
                    "database. No new leads were added."
                ),
                skipped_duplicates=skipped_dupes,
            )

        stats = self._count_contact_stats(leads)
        dashboard = build_scrape_dashboard(scrape_metrics)

        whatsapp_previews: list[WhatsAppLeadPreview] = []
        messages_generated = 0

        if data.auto_generate_whatsapp:
            if data.campaign_id:
                campaign = self.campaign_repository.get_by_id(user.id, data.campaign_id)
                if not campaign:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Campaign not found.",
                    )

            eligible = [
                lead
                for lead in leads
                if lead.phone and is_whatsapp_ready(lead.phone, lead.country)
            ]
            total_msg = len(eligible)
            prog(90, "whatsapp", f"Generating AI WhatsApp messages (0/{total_msg})...")

            cv = None
            whatsapp_errors: list[str] = []
            try:
                cv = self._require_cv(user)
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                whatsapp_errors.append(detail)
                logger.warning("Skipping WhatsApp AI for scrape: %s", detail)

            if cv:
                for index, lead in enumerate(eligible, start=1):
                    pct = 90 + int(9 * index / max(total_msg, 1))
                    prog(
                        pct,
                        "whatsapp",
                        f"Generating AI message {index}/{total_msg} for {lead.company_name}...",
                    )
                    try:
                        display_message, stored_content = self.groq_service.generate_message(
                            lead, cv, MessageType.whatsapp
                        )
                    except HTTPException as exc:
                        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                        whatsapp_errors.append(detail)
                        logger.warning("WhatsApp AI skipped for lead %s: %s", lead.id, detail)
                        continue
                    except Exception as exc:
                        whatsapp_errors.append(str(exc))
                        logger.warning("WhatsApp AI skipped for lead %s: %s", lead.id, exc)
                        continue

                    self.message_repository.create(
                        user.id,
                        {
                            "lead_id": lead.id,
                            "campaign_id": data.campaign_id,
                            "message_type": MessageType.whatsapp,
                            "message_content": stored_content,
                        },
                    )
                    messages_generated += 1
                    whatsapp_previews.append(
                        WhatsAppLeadPreview(
                            lead_id=lead.id,
                            company_name=lead.company_name,
                            phone=lead.phone,
                            message=display_message,
                            whatsapp_url=build_whatsapp_link(lead.phone, display_message),
                        )
                    )

            if whatsapp_errors and not messages_generated and cv:
                message = self._build_summary_message(
                    len(leads),
                    stats,
                    messages_generated,
                    maps_count,
                    search_count,
                    skipped_dupes,
                    meta_count,
                    leads_discovered=leads_discovered,
                    filtered_unverified=filtered_unverified,
                    filtered_website=filtered_website,
                )
                message += (
                    " WhatsApp AI messages could not be generated (Groq connection issue). "
                    "Leads were saved successfully — retry messages later from Campaigns."
                )
                prog(100, "done", "Scraping completed (AI messages skipped)")
                return ScraperStartResponse(
                    success=True,
                    count=len(leads),
                    message=message,
                    leads_discovered=leads_discovered,
                    filtered_unverified=filtered_unverified,
                    filtered_website=filtered_website,
                    skipped_duplicates=skipped_dupes,
                    emails_found=stats["emails"],
                    whatsapp_numbers_found=stats["whatsapp"],
                    linkedin_found=stats["linkedin"],
                    with_website=stats["with_website"],
                    without_website=stats["without_website"],
                    google_maps_count=maps_count,
                    google_search_count=search_count,
                    meta_ads_count=meta_count,
                    messages_generated=messages_generated,
                    whatsapp_previews=whatsapp_previews,
                    scrape_metrics=dashboard,
                    saved_lead_ids=[lead.id for lead in leads],
                )

        prog(100, "done", "Scraping completed!")
        message = self._build_summary_message(
            len(leads),
            stats,
            messages_generated,
            maps_count,
            search_count,
            skipped_dupes,
            meta_count,
            leads_discovered=leads_discovered,
            filtered_unverified=filtered_unverified,
            filtered_website=filtered_website,
        )
        return ScraperStartResponse(
            success=True,
            count=len(leads),
            message=message,
            leads_discovered=leads_discovered,
            filtered_unverified=filtered_unverified,
            filtered_website=filtered_website,
            skipped_duplicates=skipped_dupes,
            emails_found=stats["emails"],
            whatsapp_numbers_found=stats["whatsapp"],
            linkedin_found=stats["linkedin"],
            with_website=stats["with_website"],
            without_website=stats["without_website"],
            google_maps_count=maps_count,
            google_search_count=search_count,
            meta_ads_count=meta_count,
            messages_generated=messages_generated,
            whatsapp_previews=whatsapp_previews,
            scrape_metrics=dashboard,
            saved_lead_ids=[lead.id for lead in leads],
            intelligence_stats=intel_stats,
        )

    def _require_cv(self, user: User):
        cv = self.cv_repository.get_latest_by_user(user.id)
        if not cv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload your CV first to auto-generate WhatsApp messages.",
            )
        from app.models.user_api_key import ApiProvider

        has_groq = bool(self.rotation.get_user_tokens(user.id, ApiProvider.groq))
        if not has_groq:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Groq API key required. Add your own Groq key in Settings → API Keys.",
            )
        return cv

    def _count_contact_stats(self, leads: list[Lead]) -> dict[str, int]:
        emails = sum(1 for lead in leads if lead.email and is_valid_email(lead.email))
        whatsapp = sum(
            1 for lead in leads if lead.phone and is_whatsapp_ready(lead.phone, lead.country)
        )
        linkedin = sum(1 for lead in leads if lead.linkedin_url)
        with_website = sum(1 for lead in leads if has_real_website(lead.website))
        without_website = len(leads) - with_website
        return {
            "emails": emails,
            "whatsapp": whatsapp,
            "linkedin": linkedin,
            "with_website": with_website,
            "without_website": without_website,
        }

    def _build_summary_message(
        self,
        total: int,
        stats: dict[str, int],
        messages_generated: int,
        maps_count: int = 0,
        search_count: int = 0,
        skipped_duplicates: int = 0,
        meta_count: int = 0,
        *,
        leads_discovered: int = 0,
        filtered_unverified: int = 0,
        filtered_website: int = 0,
    ) -> str:
        parts: list[str] = []
        if leads_discovered and leads_discovered != total:
            parts.append(f"Discovered {leads_discovered} lead(s), saved {total} new")
        else:
            parts.append(f"Imported {total} new lead(s)")
        if filtered_unverified:
            parts.append(f"{filtered_unverified} skipped (no verified email/WhatsApp)")
        if filtered_website:
            parts.append(f"{filtered_website} skipped (website filter)")
        if skipped_duplicates:
            parts.append(f"{skipped_duplicates} duplicate(s) skipped")
        if maps_count or search_count or meta_count:
            source_bits = []
            if maps_count:
                source_bits.append(f"{maps_count} Maps")
            if search_count:
                source_bits.append(f"{search_count} Internet")
            if meta_count:
                source_bits.append(f"{meta_count} Meta Ads")
            parts.append("Sources: " + ", ".join(source_bits))
        parts.append(f"{stats['emails']} verified emails")
        parts.append(f"{stats['whatsapp']} verified WhatsApp numbers")
        parts.append(f"{stats['linkedin']} LinkedIn profiles")
        parts.append(f"{stats['with_website']} with website")
        parts.append(f"{stats['without_website']} without website")
        if messages_generated:
            parts.append(f"{messages_generated} WhatsApp messages generated")
        return ". ".join(parts) + "."
