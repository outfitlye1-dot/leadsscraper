from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.brain_repository import BrainRepository
from app.repositories.cv_repository import CVRepository
from app.schemas.brain import BrainGenerateResponse, BrainProfileResponse, BrainUpdateRequest
from app.services.groq_service import GroqService


class BrainService:
    def __init__(self, db: Session):
        self.brain_repository = BrainRepository(db)
        self.cv_repository = CVRepository(db)
        self.groq_service = GroqService(db)

    def _to_profile_dict(self, brain) -> dict:
        return {
            "name": brain.name,
            "skills": brain.skills or [],
            "experience": brain.experience or [],
            "education": brain.education or [],
            "projects": brain.projects or [],
            "services": brain.services or [],
            "tools": brain.tools or [],
            "technologies": brain.technologies or [],
            "professional_summary": brain.professional_summary,
            "pricing_currency": brain.pricing_currency or "USD",
            "pricing_high": brain.pricing_high,
            "pricing_floor": brain.pricing_floor,
        }

    def get_brain(self, user: User) -> BrainProfileResponse | None:
        brain = self.brain_repository.get_by_user(user.id)
        if not brain:
            return None
        return BrainProfileResponse.model_validate(brain)

    def update_brain(self, user: User, data: BrainUpdateRequest) -> BrainProfileResponse:
        payload = data.model_dump(exclude_unset=True)
        brain = self.brain_repository.upsert(user.id, payload)
        return BrainProfileResponse.model_validate(brain)

    def import_from_cv(self, user: User) -> BrainProfileResponse:
        cv = self.cv_repository.get_latest_by_user(user.id)
        if not cv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No CV found. Upload a CV first or enter data manually.",
            )

        payload = {
            "name": cv.name,
            "skills": cv.skills,
            "experience": cv.experience,
            "education": cv.education,
            "projects": cv.projects,
            "services": cv.services,
            "tools": cv.tools,
            "technologies": cv.technologies,
            "professional_summary": cv.professional_summary,
        }
        brain = self.brain_repository.upsert(user.id, payload)
        return BrainProfileResponse.model_validate(brain)

    def generate_brain(self, user: User) -> BrainGenerateResponse:
        self.groq_service.user_id = user.id
        brain = self.brain_repository.get_by_user(user.id)
        if not brain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Save your brain profile data first before generating.",
            )

        profile = self._to_profile_dict(brain)
        if not profile.get("name") and not profile.get("professional_summary"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Add at least a name or professional summary to generate a brain.",
            )

        system_prompt = self.groq_service.generate_brain_prompt(
            profile, brain.custom_notes or ""
        )
        brain = self.brain_repository.upsert(user.id, {"system_prompt": system_prompt})
        return BrainGenerateResponse(system_prompt=brain.system_prompt or system_prompt)
