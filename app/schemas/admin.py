from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.schemas.user import UserResponse


class AdminDashboardResponse(BaseModel):
    total_users: int
    admin_users: int
    regular_users: int
    total_leads: int
    total_campaigns: int
    total_messages: int
    total_api_keys: int
    total_outreach_emails: int
    total_outreach_campaigns: int
    active_scraper_jobs: int
    outreach_worker_enabled: bool


class AdminUserStatsResponse(BaseModel):
    leads: int = 0
    campaigns: int = 0
    messages: int = 0
    api_keys: int = 0
    outreach_emails: int = 0
    email_accounts: int = 0


class AdminUserListItem(UserResponse):
    lead_count: int = 0
    campaign_count: int = 0


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int
    page: int
    page_size: int


class AdminUserDetailResponse(UserResponse):
    stats: AdminUserStatsResponse


class AdminUserCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.user


class AdminUserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None


class AdminLeadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_email: str | None = None
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    status: str
    is_saved: bool
    created_at: datetime


class AdminLeadListResponse(BaseModel):
    items: list[AdminLeadListItem]
    total: int
    page: int
    page_size: int


class AdminScraperJobResponse(BaseModel):
    job_id: str
    user_id: int
    user_email: str | None = None
    status: str
    mode: str
    progress: int
    stage: str
    message: str
    created_at: datetime
    updated_at: datetime


class AdminScraperJobListResponse(BaseModel):
    items: list[AdminScraperJobResponse]


class AdminOutreachSummaryResponse(BaseModel):
    total_accounts: int
    connected_accounts: int
    agents_running: int
    emails_sent: int
    emails_queued: int
    replies_received: int
    pending_jobs: int


class AdminSystemResponse(BaseModel):
    app_name: str
    app_version: str
    database_url: str
    outreach_worker_enabled: bool
    smtp_configured: bool
    google_oauth_configured: bool
    microsoft_oauth_configured: bool
    scraper_workers: int
    scraper_fast_mode: bool
