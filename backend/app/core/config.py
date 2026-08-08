from pathlib import Path

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Meta Ads still uses Apify; Google Maps uses local Playwright only
    APIFY_META_ADS_ACTOR_ID: str = "scrapemint/facebook-ads-library-scraper"

    DATABASE_URL: str = "sqlite:///./leadgen.db"

    # local | production — affects CORS merging and prod safety defaults
    ENVIRONMENT: str = "local"

    CORS_ORIGINS: str = "*"

    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    EXPORT_DIR: str = "exports"

    SCRAPER_WORKERS: int = 30
    SCRAPER_MIN_WORKERS: int = 8
    SCRAPER_MAX_WORKERS: int = 40
    SCRAPER_SEARCH_MAX_WORKERS: int = 40
    SCRAPER_TIMEOUT: float = 8.0
    SCRAPER_FETCH_RETRIES: int = 1
    SCRAPER_DELAY_MIN_MS: int = 40
    SCRAPER_DELAY_MAX_MS: int = 180
    SCRAPER_ENABLE_PLAYWRIGHT: bool = True
    SCRAPER_PLAYWRIGHT_TIMEOUT: float = 8.0
    SCRAPER_VERIFY_EMAIL_MX: bool = False
    SCRAPER_BING_PAGES: int = 1
    SCRAPER_DISCOVERY_MULTIPLIER: int = 2
    SCRAPER_CRAWL_SEED_MULTIPLIER: float = 2.0
    SCRAPER_FAST_MODE: bool = False
    # Extra free internet engines: brave,yahoo,mojeek (+ searxng if URL set)
    SCRAPER_EXTRA_ENGINES: str = "brave,yahoo,mojeek"
    SCRAPER_SEARXNG_URL: str = ""
    # Overlap multi-engine search with parallel website crawls under high load
    SCRAPER_INTERNET_PIPELINE: bool = True
    SCRAPER_PIPELINE_CRAWL_START: int = 4
    # Hard wall-clock cap so Internet scrapes finish instead of hanging
    SCRAPER_INTERNET_MAX_SECONDS: float = 75.0
    SCRAPER_PROXY_URLS: str = ""
    SCRAPER_RESPECT_ROBOTS: bool = True
    SCRAPER_MAX_CRAWL_DEPTH: int = 1
    SCRAPER_MAX_CRAWL_URLS: int = 8
    SCRAPER_PLAYWRIGHT_CONTEXTS: int = 3
    # Google Maps via Playwright (https://github.com/kevmaindev/Googles-Maps-Scraper)
    SCRAPER_PLAYWRIGHT_MAPS_HEADLESS: bool = True
    # Give Maps enough time when it is the only source (Railway)
    SCRAPER_PLAYWRIGHT_MAPS_MAX_SECONDS: float = 75.0
    # Keep at 1 on Railway/Docker — 2+ Chromiums often OOM ("Target crashed")
    SCRAPER_PLAYWRIGHT_MAPS_CONCURRENCY: int = 1
    SCRAPER_PLAYWRIGHT_MAPS_RETRIES: int = 2
    # Parallel Maps+Internet uses multiple Chromiums — disable on small hosts
    SCRAPER_PARALLEL_SOURCES: bool = True
    # Only applies when scrape_source=all (Maps-only never runs Internet)
    SCRAPER_INTERNET_BEFORE_MAPS: bool = False
    SCRAPER_CHECKPOINT_ENABLED: bool = True
    SCRAPER_AI_SELECTORS: bool = True

    APP_NAME: str = "AI Lead Generation SaaS"
    APP_VERSION: str = "1.0.0"

    OTP_EXPIRE_MINUTES: int = 10
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_VERIFY_ATTEMPTS: int = 5
    OTP_DEV_MODE: bool = False

    # Gmail SMTP (App Password — https://myaccount.google.com/apppasswords)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "LeadGen AI"

    # Email outreach OAuth (user connects their own accounts)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:3000/api/email-outreach/oauth/google/callback"
    GOOGLE_AUTH_REDIRECT_URI: str = "http://localhost:3000/api/auth/google/callback"
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_OAUTH_REDIRECT_URI: str = "http://localhost:3000/api/email-outreach/oauth/microsoft/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # Bootstrap admin account on startup (set in .env)
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_NAME: str = "Admin"

    # Pro plan (optional checkout URL for Stripe/PayPal etc.)
    PRO_PLAN_PRICE_USD: float = 29.0
    PRO_PLAN_PRICE_PKR: float = 8500.0
    PRO_PLAN_CHECKOUT_URL: str = ""
    PRO_PLAN_CONTACT_EMAIL: str = ""
    BACKEND_PUBLIC_URL: str = "http://127.0.0.1:8001"

    # JazzCash (Pakistan) — sandbox credentials from https://sandbox.jazzcash.com.pk
    JAZZCASH_MERCHANT_ID: str = ""
    JAZZCASH_PASSWORD: str = ""
    JAZZCASH_INTEGRITY_SALT: str = ""
    JAZZCASH_SANDBOX: bool = True
    JAZZCASH_VERSION: str = "1.1"
    JAZZCASH_TXN_TYPE: str = "MWALLET"

    # WhatsApp Cloud API (Meta) — never commit real tokens; set in .env
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_API_VERSION: str = "v21.0"
    WHATSAPP_TEST_DISPLAY_NUMBER: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "leadgen_wa_verify"

    # WhatsApp Web (Playwright) — OPTIONAL; default off. Does not affect Cloud API.
    WA_WEB_ENABLED: bool = False
    WA_WEB_PROFILE_DIR: str = "data/wa_web_profile"
    WA_WEB_HEADLESS: bool = False
    WA_WEB_POLL_SECONDS: int = 3
    WA_WEB_AUTO_START_WORKER: bool = True
    WA_WEB_USER_ID: int = 0
    WA_WEB_USER_EMAIL: str = ""
    WA_WEB_MAX_REPLIES_PER_MIN: int = 8
    WA_WEB_TYPING_DELAY_MS: int = 40
    # Prefer installed Google Chrome (better WhatsApp Business linking than Chromium)
    WA_WEB_USE_CHROME: bool = True
    # Attach to real Chrome (run scripts/launch_wa_chrome.ps1). Best for Business "Couldn't link".
    WA_WEB_CDP_URL: str = ""

    # Background outreach worker (off by default on local SQLite to keep login/API fast)
    OUTREACH_WORKER_ENABLED: bool = False
    OUTREACH_WORKER_POLL_SECONDS: int = 3
    OUTREACH_SYNC_INTERVAL_SECONDS: int = 60

    @model_validator(mode="after")
    def normalize_database_url(self) -> "Settings":
        """Railway/Heroku often provide postgres:// — normalize for SQLAlchemy + psycopg3."""
        url = (self.DATABASE_URL or "").strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://") and "+psycopg" not in url and "+asyncpg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        self.DATABASE_URL = url
        return self

    @model_validator(mode="after")
    def default_outreach_worker(self) -> "Settings":
        """Enable outreach worker automatically only outside local SQLite dev."""
        if "sqlite" not in self.DATABASE_URL.lower():
            self.OUTREACH_WORKER_ENABLED = True
        return self

    @model_validator(mode="after")
    def normalize_smtp(self) -> "Settings":
        if self.SMTP_PASSWORD:
            self.SMTP_PASSWORD = self.SMTP_PASSWORD.strip().strip('"').strip("'")
        if self.SMTP_USER and not self.SMTP_FROM:
            self.SMTP_FROM = self.SMTP_USER
        return self

    @property
    def smtp_configured(self) -> bool:
        return bool(self.SMTP_USER and self.SMTP_PASSWORD)

    @property
    def whatsapp_cloud_configured(self) -> bool:
        return bool(self.WHATSAPP_ACCESS_TOKEN.strip() and self.WHATSAPP_PHONE_NUMBER_ID.strip())

    @property
    def effective_otp_dev_mode(self) -> bool:
        """Log OTP to console when SMTP is missing (local sqlite dev)."""
        if self.OTP_DEV_MODE:
            return True
        return not self.smtp_configured and "sqlite" in self.DATABASE_URL.lower()

    @property
    def is_production(self) -> bool:
        return (self.ENVIRONMENT or "").strip().lower() in {"production", "prod"}

    @property
    def cors_origins_list(self) -> list[str]:
        defaults = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]
        frontend = (self.FRONTEND_URL or "").strip().rstrip("/")
        extras = [frontend] if frontend else []

        if self.CORS_ORIGINS.strip() == "*":
            if self.is_production and extras:
                return list(dict.fromkeys(extras))
            return list(dict.fromkeys([*defaults, *extras]))

        configured = [origin.strip().rstrip("/") for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.is_production:
            return list(dict.fromkeys([*configured, *extras]))
        return list(dict.fromkeys([*configured, *defaults, *extras]))

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def get_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env", override=True)
    return Settings()
