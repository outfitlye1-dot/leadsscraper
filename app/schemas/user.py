from typing import Literal

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserPlan, UserRole
from app.schemas.payment import PaymentMethodResponse


class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "password": "SecurePass123!",
                }
            ]
        }
    )

    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class OtpSendRequest(BaseModel):
    email: EmailStr
    purpose: Literal["login", "register", "reset_password"] = "login"


class OtpSendResponse(BaseModel):
    message: str
    expires_in_minutes: int


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    purpose: Literal["login", "register", "reset_password"] = "login"
    name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class OAuthStartResponse(BaseModel):
    url: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    )

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    avatar_url: str | None = None
    role: UserRole
    api_access: bool = True
    plan: UserPlan = UserPlan.free
    daily_token_limit: int = 50
    tokens_used_today: int = 0
    tokens_remaining: int | None = None
    own_api_keys_enabled: bool = False
    own_api_keys_requested: bool = False
    paid_plan_requested: bool = False
    created_at: datetime
    updated_at: datetime


class UsageQuotaResponse(BaseModel):
    plan: str
    daily_token_limit: int
    tokens_used_today: int
    tokens_remaining: int
    tokens_reset_on: str
    api_access: bool
    own_api_keys_enabled: bool
    own_api_keys_requested: bool
    paid_plan_requested: bool = False
    is_unlimited: bool
    paid_plan_tokens: int


class PlanOptionResponse(BaseModel):
    id: str
    name: str
    price_usd: float
    daily_tokens: int
    features: list[str]
    is_current: bool = False


class PlansCatalogResponse(BaseModel):
    current_plan: str
    paid_plan_requested: bool
    checkout_url: str | None = None
    contact_email: str | None = None
    price_pkr: float | None = None
    payment_methods: list[PaymentMethodResponse] = []
    plans: list[PlanOptionResponse]


class PurchaseProPlanResponse(BaseModel):
    action: Literal["redirect", "request", "already_active", "jazzcash_form"]
    checkout_url: str | None = None
    post_url: str | None = None
    fields: dict[str, str] | None = None
    txn_ref_no: str | None = None
    amount_pkr: float | None = None
    message: str
    usage: UsageQuotaResponse | None = None
