from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BrainProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    skills: list | None
    experience: list | None
    education: list | None
    projects: list | None
    services: list | None
    tools: list | None
    technologies: list | None
    professional_summary: str | None
    custom_notes: str | None
    system_prompt: str | None
    pricing_currency: str | None = "USD"
    pricing_high: float | None = None
    pricing_floor: float | None = None
    created_at: datetime
    updated_at: datetime


class BrainUpdateRequest(BaseModel):
    name: str | None = None
    skills: list[str] | None = None
    experience: list | dict | None = None
    education: list | dict | None = None
    projects: list | dict | None = None
    services: list[str] | None = None
    tools: list[str] | None = None
    technologies: list[str] | None = None
    professional_summary: str | None = None
    custom_notes: str | None = None
    system_prompt: str | None = None
    pricing_currency: str | None = None
    pricing_high: float | None = None
    pricing_floor: float | None = None

    @field_validator("pricing_currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        return cleaned[:10] or "USD"

    @field_validator("pricing_high", "pricing_floor")
    @classmethod
    def non_negative(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("Pricing must be zero or positive")
        return float(value)

    @model_validator(mode="after")
    def high_above_floor(self) -> "BrainUpdateRequest":
        high = self.pricing_high
        floor = self.pricing_floor
        if high is not None and floor is not None and high < floor:
            raise ValueError("Opening (high) price must be greater than or equal to floor price")
        return self


class BrainGenerateResponse(BaseModel):
    system_prompt: str = Field(..., description="AI-generated brain/system prompt")
    message: str = "Brain prompt generated successfully"
