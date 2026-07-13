from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.scrape_sources import ScrapeSourceMode, build_internet_search_query
from app.utils.website_utils import WebsiteFilter


class ScraperStartRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "keyword": "Web Design Agency",
                    "location": "London, United Kingdom",
                    "limit": 100,
                    "enrich_contacts": True,
                    "auto_generate_whatsapp": True,
                }
            ]
        }
    )

    keyword: str = Field(default="", max_length=255)
    location: str = Field(default="", max_length=255)
    search_query: str | None = Field(
        None,
        max_length=500,
        description="Full internet search query (for Internet-only source)",
    )
    limit: int = Field(100, ge=1, le=500)
    enrich_contacts: bool = Field(
        True,
        description="Extract & validate emails, WhatsApp numbers, LinkedIn from websites",
    )
    only_verified_contacts: bool = Field(
        False,
        description="Only save leads with verified email or WhatsApp mobile number",
    )
    auto_generate_whatsapp: bool = Field(
        False,
        description="Auto-generate WhatsApp messages and wa.me links after scraping",
    )
    campaign_id: int | None = Field(None, description="Optional campaign to tag messages")
    website_filter: WebsiteFilter = Field(
        WebsiteFilter.without_website,
        description="Always targets businesses without a real website",
    )
    scrape_source: ScrapeSourceMode = Field(
        ScrapeSourceMode.all,
        description="google_maps (Apify), google_search (Internet), meta_ads, or all",
    )
    include_meta_ads: bool = Field(
        False,
        description="When using All sources, optionally also discover businesses from Meta Ad Library",
    )

    @model_validator(mode="after")
    def validate_source_fields(self) -> "ScraperStartRequest":
        has_query = bool(self.search_query and self.search_query.strip())
        has_keyword = bool(self.keyword.strip())
        has_location = bool(self.location.strip())

        if self.scrape_source == ScrapeSourceMode.google_search:
            if not has_query and has_keyword and has_location:
                self.search_query = build_internet_search_query(self.keyword, self.location)
            elif not has_query and not (has_keyword and has_location):
                raise ValueError(
                    "Internet scraper needs Keyword and Location (same as Maps — free search)"
                )
        elif self.scrape_source == ScrapeSourceMode.meta_ads:
            if not has_query and not has_keyword:
                raise ValueError(
                    "Meta Ads scraper needs a keyword or search query "
                    '(e.g. "wedding planner")'
                )
            if not has_location:
                raise ValueError("Meta Ads scraper needs a country/location for Ad Library")
        elif not (has_keyword and has_location):
            raise ValueError("Google Maps requires both Keyword and Location")
        return self


class WhatsAppLeadPreview(BaseModel):
    lead_id: int
    company_name: str
    phone: str
    message: str
    whatsapp_url: str


class ScrapeMetricsResponse(BaseModel):
    total_pages_scanned: int = 0
    total_leads_found: int = 0
    valid_emails_found: int = 0
    success_rate: float = 0.0
    failed_requests: int = 0
    pages_discovered: int = 0
    pages_fetched: int = 0
    pages_failed: int = 0
    leads_parsed: int = 0
    leads_rejected: int = 0
    leads_saved: int = 0
    valid_emails: int = 0
    valid_phones: int = 0
    whatsapp_ready: int = 0
    high_quality: int = 0
    medium_quality: int = 0
    low_quality: int = 0
    validation_errors: list[str] = Field(default_factory=list)
    failed_urls: list[str] = Field(default_factory=list)
    pages_crawled: int = 0
    requests_per_minute: float = 0.0
    retry_count: int = 0
    browser_renders: int = 0
    js_render_used: int = 0
    images_downloaded: int = 0
    active_workers: int = 0
    queue_size: int = 0
    bot_blocks: int = 0
    proxy_switches: int = 0
    strategy_http: int = 0
    strategy_playwright: int = 0
    strategy_api: int = 0


class ScraperStartResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "count": 100,
                    "message": "Imported 85 enriched contacts. 40 valid emails...",
                    "emails_found": 40,
                    "whatsapp_numbers_found": 35,
                    "linkedin_found": 10,
                    "messages_generated": 30,
                    "whatsapp_previews": [],
                }
            ]
        }
    )

    success: bool
    count: int
    message: str = ""
    leads_discovered: int = 0
    filtered_unverified: int = 0
    filtered_website: int = 0
    skipped_duplicates: int = 0
    emails_found: int = 0
    whatsapp_numbers_found: int = 0
    linkedin_found: int = 0
    with_website: int = 0
    without_website: int = 0
    google_maps_count: int = 0
    google_search_count: int = 0
    meta_ads_count: int = 0
    messages_generated: int = 0
    whatsapp_previews: list[WhatsAppLeadPreview] = Field(default_factory=list)
    scrape_metrics: ScrapeMetricsResponse | None = None
    saved_lead_ids: list[int] = Field(default_factory=list)
    intelligence_stats: dict | None = None


class ScraperJobStartResponse(BaseModel):
    job_id: str


class DemoScrapeRequest(BaseModel):
    keyword: str = Field(default="web design agency", max_length=120)
    location: str = Field(default="Berlin, Germany", max_length=120)


class DemoLeadItem(BaseModel):
    company_name: str
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    city: str | None = None
    country: str | None = None
    verified: bool = False


class DemoScrapeResponse(BaseModel):
    success: bool
    count: int
    total_estimated: int = 0
    message: str = ""
    leads: list[DemoLeadItem] = Field(default_factory=list)


class DailyScrapeStatusResponse(BaseModel):
    can_run: bool
    leads_target: int = 100
    run_date: str
    last_run_date: str | None = None
    last_job_id: str | None = None
    preview_search_query: str = ""
    profile_name: str | None = None
    has_profile: bool = False


class DailyScrapeStartResponse(BaseModel):
    job_id: str
    leads_target: int = 100
    search_query: str
    message: str = ""


class ScraperLogEntry(BaseModel):
    seq: int
    ts: str
    level: str = "info"
    stage: str = ""
    text: str


class ScraperJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "paused", "completed", "failed", "cancelled"]
    mode: Literal["single", "auto"] = "single"
    progress: int
    stage: str
    message: str
    result: ScraperStartResponse | None = None
    error: str | None = None
    iteration: int = 0
    auto_kept_total: int = 0
    auto_deleted_total: int = 0
    auto_scraped_total: int = 0
    cancel_requested: bool = False
    pause_requested: bool = False
    live_metrics: ScrapeMetricsResponse | None = None
    failed_urls: list[str] = Field(default_factory=list)
    logs: list[ScraperLogEntry] = Field(default_factory=list)


class ScraperJobControlResponse(BaseModel):
    success: bool
    message: str
    job_id: str


class ScraperJobHistoryResponse(BaseModel):
    jobs: list[ScraperJobStatusResponse] = Field(default_factory=list)


class AutoScrapeStartRequest(ScraperStartRequest):
    interval_seconds: int = Field(
        default=15,
        ge=5,
        le=120,
        description="Seconds to wait between scrape rounds",
    )


class AutoScrapeStopResponse(BaseModel):
    success: bool
    message: str


class BackgroundScrapeStatusResponse(BaseModel):
    active: bool
    running: bool
    total_saved: int = 0
    iteration: int = 0
    last_query: str = ""
    progress: int = 0
    stage: str = "idle"
    message: str = ""
    logs: list[ScraperLogEntry] = Field(default_factory=list)


class LeadDatabaseSummaryItem(BaseModel):
    id: int
    company_name: str
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    created_at: str
    keyword: str | None = None
    location: str | None = None


class LeadDatabaseStatsResponse(BaseModel):
    database_name: str
    database_type: str
    database_size_bytes: int | None = None
    total_leads: int = 0
    inbox_leads: int = 0
    saved_leads: int = 0
    background_leads: int = 0
    manual_leads: int = 0
    with_phone: int = 0
    without_website: int = 0
    background_active: bool = False
    background_running: bool = False
    background_total_saved: int = 0
    background_iteration: int = 0
    background_last_query: str = ""
    recent_background: list[LeadDatabaseSummaryItem] = Field(default_factory=list)


class DashboardStatsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total_leads": 150,
                    "new_leads": 80,
                    "contacted_leads": 40,
                    "interested_leads": 20,
                    "closed_leads": 10,
                    "campaign_count": 5,
                    "messages_generated": 75,
                }
            ]
        }
    )

    total_leads: int
    new_leads: int
    contacted_leads: int
    interested_leads: int
    closed_leads: int
    follow_up_leads: int = 0
    lost_leads: int = 0
    campaign_count: int
    messages_generated: int
