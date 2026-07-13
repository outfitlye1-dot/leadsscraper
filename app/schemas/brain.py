from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class BrainGenerateResponse(BaseModel):
    system_prompt: str = Field(..., description="AI-generated brain/system prompt")
    message: str = "Brain prompt generated successfully"
