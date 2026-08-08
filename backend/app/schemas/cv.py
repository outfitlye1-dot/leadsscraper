from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.cv import CVFileType


class CVProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: CVFileType
    name: str | None
    skills: list | None
    experience: list | None
    education: list | None
    projects: list | None
    services: list | None
    tools: list | None
    technologies: list | None
    professional_summary: str | None
    skills_summary: str | None
    services_summary: str | None
    experience_summary: str | None
    created_at: datetime
    updated_at: datetime


class CVRawResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"raw_text": "John Doe\nSoftware Engineer\nSkills: Python, FastAPI..."}]
        }
    )

    raw_text: str = Field(..., description="Raw extracted text from the uploaded CV")


class CVUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    profile: CVProfileResponse
