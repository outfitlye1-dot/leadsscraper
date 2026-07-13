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

    APIFY_ACTOR_ID: str = "compass/crawler-google-places"
    APIFY_META_ADS_ACTOR_ID: str = "scrapemint/facebook-ads-library-scraper"

    DATABASE_URL: str = "sqlite:///./leadgen.db"

    CORS_ORIGINS: str = "*"

    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    EXPORT_DIR: str = "exports"

    SCRAPER_WORKERS: int = 12
    SCRAPER_MIN_WORKERS: int = 4
    SCRAPER_MAX_WORKERS: int = 24
    SCRAPER_SEARCH_MAX_WORKERS: int = 10
    SCRAPER_TIMEOUT: float = 10.0
    SCRAPER_FETCH_RETRIES: int = 2
    SCRAPER_DELAY_MIN_MS: int = 60
    SCRAPER_DELAY_MAX_MS: int = 280
    SCRAPER_ENABLE_PLAYWRIGHT: bool = True
    SCRAPER_PLAYWRIGHT_TIMEOUT: float = 14.0
    SCRAPER_VERIFY_EMAIL_MX: bool = False
    SCRAPER_BING_PAGES: int = 4
    SCRAPER_DISCOVERY_MULTIPLIER: int = 4
    SCRAPER_CRAWL_SEED_MULTIPLIER: float = 3.0
    SCRAPER_FAST_MODE: bool = True
    SCRAPER_PROXY_URLS: str = ""
    SCRAPER_RESPECT_ROBOTS: bool = True
    SCRAPER_MAX_CRAWL_DEPTH: int = 2
    SCRAPER_MAX_CRAWL_URLS: int = 30
    SCRAPER_PLAYWRIGHT_CONTEXTS: int = 3
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
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_OAUTH_REDIRECT_URI: str = "http://localhost:3000/api/email-outreach/oauth/microsoft/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # Bootstrap admin account on startup (set in .env)
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_NAME: str = "Admin"

    # Background outreach worker (off by default on local SQLite to keep login/API fast)
    OUTREACH_WORKER_ENABLED: bool = False
    OUTREACH_WORKER_POLL_SECONDS: int = 15
    OUTREACH_SYNC_INTERVAL_SECONDS: int = 300

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
    def effective_otp_dev_mode(self) -> bool:
        """Log OTP to console when SMTP is missing (local sqlite dev)."""
        if self.OTP_DEV_MODE:
            return True
        return not self.smtp_configured and "sqlite" in self.DATABASE_URL.lower()

    @property
    def cors_origins_list(self) -> list[str]:
        defaults = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]
        if self.CORS_ORIGINS.strip() == "*":
            return defaults

        configured = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        merged = list(dict.fromkeys([*configured, *defaults]))
        return merged

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def get_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env", override=True)
    return Settings()
