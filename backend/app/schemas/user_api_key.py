from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user_api_key import ApiKeyStatus, ApiProvider


class UserApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: ApiProvider
    label: str
    masked_key: str
    priority: int
    status: ApiKeyStatus
    usage_count: int
    last_error: str | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserApiKeyCreateRequest(BaseModel):
    provider: ApiProvider
    api_key: str = Field(..., min_length=8, max_length=500)
    label: str = Field(default="API Key", max_length=120)


class UserApiKeyBulkCreateRequest(BaseModel):
    provider: ApiProvider
    api_keys: list[str] = Field(..., min_length=1, max_length=50)
    label_prefix: str = Field(default="Key", max_length=80)


class UserApiKeyUpdateRequest(BaseModel):
    label: str | None = Field(None, max_length=120)
    priority: int | None = None
    status: ApiKeyStatus | None = None


class UserApiKeyBulkCreateResponse(BaseModel):
    created: int
    keys: list[UserApiKeyResponse]
