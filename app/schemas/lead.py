from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.lead import LeadStatus


class LeadContactLinks(BaseModel):
    whatsapp_url: str | None = None
    email_url: str | None = None
    linkedin_url: str | None = None
    facebook_url: str | None = None
    instagram_url: str | None = None
    website_url: str | None = None
    needs_website_pitch: bool = False
    website_offer_whatsapp_url: str | None = None
    website_offer_email_url: str | None = None
    offer_message: str | None = None


class LeadCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "company_name": "Acme Corp",
                    "contact_name": "John Smith",
                    "phone": "+1234567890",
                    "email": "john@acme.com",
                    "website": "https://acme.com",
                    "city": "Karachi",
                    "country": "Pakistan",
                    "industry": "Technology",
                    "notes": "Met at conference",
                    "source": "manual",
                    "status": "new",
                }
            ]
        }
    )

    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    website: str | None = Field(None, max_length=500)
    linkedin_url: str | None = Field(None, max_length=500)
    facebook_url: str | None = Field(None, max_length=500)
    instagram_url: str | None = Field(None, max_length=500)
    address: str | None = Field(None, max_length=500)
    postal_code: str | None = Field(None, max_length=20)
    category: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    industry: str | None = Field(None, max_length=100)
    notes: str | None = None
    source: str | None = Field(None, max_length=100)
    status: LeadStatus = LeadStatus.new


class LeadUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "contact_name": "Jane Smith",
                    "status": "contacted",
                    "notes": "Sent initial outreach",
                }
            ]
        }
    )

    company_name: str | None = Field(None, min_length=1, max_length=255)
    contact_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    website: str | None = Field(None, max_length=500)
    linkedin_url: str | None = Field(None, max_length=500)
    facebook_url: str | None = Field(None, max_length=500)
    instagram_url: str | None = Field(None, max_length=500)
    address: str | None = Field(None, max_length=500)
    postal_code: str | None = Field(None, max_length=20)
    category: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    industry: str | None = Field(None, max_length=100)
    notes: str | None = None
    source: str | None = Field(None, max_length=100)
    status: LeadStatus | None = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    contact_name: str | None
    phone: str | None
    email: str | None
    website: str | None
    linkedin_url: str | None
    facebook_url: str | None
    instagram_url: str | None
    address: str | None
    postal_code: str | None
    category: str | None
    city: str | None
    country: str | None
    industry: str | None
    notes: str | None
    source: str | None
    status: LeadStatus
    quality_score: int | None = None
    quality_tier: str | None = None
    whatsapp_ready: bool | None = None
    phone_verified: bool | None = None
    email_verified: bool | None = None
    website_quality_score: int | None = None
    website_opportunity_score: int | None = None
    website_problems: list | None = None
    reviews_count: int | None = None
    rating: float | None = None
    business_hours: str | None = None
    google_profile_score: int | None = None
    photos_count: int | None = None
    buying_intent_score: int | None = None
    intent_tier: str | None = None
    social_activity_score: int | None = None
    social_links_verified: bool | None = None
    is_running_ads: bool | None = None
    ads_count: int | None = None
    ad_platform: str | None = None
    landing_page: str | None = None
    ad_activity_score: int | None = None
    ai_qualification: str | None = None
    recommended_offer: str | None = None
    qualification_reason: str | None = None
    niche_key: str | None = None
    recommended_service: str | None = None
    intelligence_meta: dict | None = None
    is_saved: bool = False
    saved_at: datetime | None = None
    contact_links: LeadContactLinks | None = None
    outreach_email_status: str = "none"
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class LeadBulkDeleteRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    select_all: bool = False


class LeadBulkSaveRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class LeadImportResponse(BaseModel):
    imported: int
    skipped_duplicates: int
    message: str


class LeadWebsiteAuditResponse(BaseModel):
    lead_id: int
    company_name: str
    website: str | None
    website_quality_score: int | None
    website_opportunity_score: int | None
    website_problems: list | None = None
    audit_label: str | None = None


class LeadQualificationResponse(BaseModel):
    lead_id: int
    company_name: str
    ai_qualification: str | None
    recommended_offer: str | None
    qualification_reason: str | None
    buying_intent_score: int | None
    intent_tier: str | None
    recommended_service: str | None


class LeadIntelligenceResponse(BaseModel):
    lead_id: int
    company_name: str
    website_audit: LeadWebsiteAuditResponse
    qualification: LeadQualificationResponse
    contact: dict
    google_maps: dict
    social: dict
    meta_ads: dict
    niche: dict
    intelligence_meta: dict | None = None
