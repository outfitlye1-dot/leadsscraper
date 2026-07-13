from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.campaign import CampaignStatus, MessageType


class SearchQueryOptimizeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    location: str | None = Field(default=None, max_length=200)


class SearchQueryOptimizeResponse(BaseModel):
    optimized_query: str
    suggestions: list[str]
    tips: str = ""
    was_corrected: bool = False


class ScrapeSuggestRequest(BaseModel):
    scrape_source: str = Field(
        default="all",
        description="google_maps | google_search | meta_ads | all",
    )


class ScrapeSuggestResponse(BaseModel):
    recommended_keyword: str
    recommended_location: str
    recommended_search_query: str
    keyword_suggestions: list[str]
    location_suggestions: list[str]
    search_queries: list[str]
    strategy_tips: str
    profile_name: str | None = None
    has_profile: bool = False
    user_location: str = Field(
        default="",
        description="City from Brain custom_notes only (never AI-suggested)",
    )


class CampaignCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Q1 Web Design Outreach",
                    "message_type": "email",
                    "status": "draft",
                }
            ]
        }
    )

    name: str = Field(..., min_length=1, max_length=255)
    message_type: MessageType
    status: CampaignStatus = CampaignStatus.draft


class CampaignUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"name": "Q1 Web Design Outreach - Active", "status": "active"}]
        }
    )

    name: str | None = Field(None, min_length=1, max_length=255)
    message_type: MessageType | None = None
    status: CampaignStatus | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    message_type: MessageType
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(CampaignResponse):
    message_count: int = 0
    eligible_leads: int = 0


class CampaignRunRequest(BaseModel):
    lead_status: str | None = Field(default="new", description="Filter leads by status")
    limit: int = Field(default=10, ge=1, le=100)
    skip_existing: bool = Field(default=True, description="Skip leads already messaged in this campaign")
    lead_ids: list[int] | None = Field(default=None, description="Optional specific lead IDs")


class CampaignRunResultItem(BaseModel):
    lead_id: int
    company_name: str
    success: bool
    message_preview: str | None = None
    whatsapp_url: str | None = None
    error: str | None = None


class CampaignRunResponse(BaseModel):
    campaign_id: int
    campaign_status: CampaignStatus
    processed: int
    generated: int
    skipped: int
    failed: int
    results: list[CampaignRunResultItem]


class MessageGenerateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"lead_id": 1, "message_type": "whatsapp", "campaign_id": None}]
        }
    )

    lead_id: int = Field(..., gt=0)
    message_type: MessageType
    campaign_id: int | None = Field(None, gt=0)


class MessageGenerateResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Hi John, I noticed Acme Corp's great work in technology. "
                    "I specialize in web design and would love to connect."
                }
            ]
        }
    )

    message: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int | None
    campaign_id: int | None
    message_type: MessageType
    message_content: str
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MessageBulkDeleteResponse(BaseModel):
    deleted: int
    message: str
