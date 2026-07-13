from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.cv import CVFileType
from app.models.user import User
from app.repositories.cv_repository import CVRepository
from app.schemas.cv import CVProfileResponse, CVRawResponse, CVUploadResponse
from app.services.groq_service import GroqService
from app.utils.file_utils import get_user_upload_path, validate_file_extension
from app.utils.text_extraction import extract_text_from_file


class CVService:
    def __init__(self, db: Session):
        self.db = db
        self.cv_repository = CVRepository(db)
        self.groq_service = GroqService(db)

    async def upload_cv(self, user: User, file: UploadFile) -> CVUploadResponse:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required",
            )

        file_type_str = validate_file_extension(file.filename)
        if not file_type_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and DOCX files are supported",
            )

        settings = get_settings()
        content = await file.read()
        if len(content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
            )

        file_path = get_user_upload_path(user.id, file.filename)
        file_path.write_bytes(content)

        raw_text = extract_text_from_file(Path(file_path), file_type_str)
        if not raw_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from the uploaded file",
            )

        from app.repositories.user_api_key_repository import UserApiKeyRepository
        from app.models.user_api_key import ApiProvider

        has_user_groq = bool(
            UserApiKeyRepository(self.db).get_active_keys(user.id, ApiProvider.groq)
        )

        self.groq_service.user_id = user.id
        parsed_profile: dict = {
            "name": None,
            "skills": [],
            "experience": [],
            "education": [],
            "projects": [],
            "services": [],
            "tools": [],
            "technologies": [],
        }
        summaries: dict = {
            "professional_summary": "",
            "skills_summary": "",
            "services_summary": "",
            "experience_summary": "",
        }

        if has_user_groq:
            try:
                parsed_profile = self.groq_service.extract_cv_profile(raw_text)
                summaries = self.groq_service.generate_summaries(parsed_profile)
            except HTTPException:
                parsed_profile, summaries = self._fallback_cv_profile(raw_text)
        else:
            parsed_profile, summaries = self._fallback_cv_profile(raw_text)

        cv_data = self._normalize_cv_data(
            {
                "original_filename": file.filename,
                "file_path": str(file_path),
                "file_type": CVFileType(file_type_str),
                "raw_text": raw_text,
                **parsed_profile,
                **summaries,
            }
        )

        try:
            cv = self.cv_repository.create_or_update(user.id, cv_data)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save CV profile: {exc}",
            ) from exc
        profile = CVProfileResponse.model_validate(cv)
        message = "CV uploaded and processed successfully"
        if not has_user_groq:
            message = "CV uploaded. Add Groq API key in Settings for full AI profile parsing."
        return CVUploadResponse(message=message, profile=profile)

    @staticmethod
    def _normalize_cv_data(data: dict) -> dict:
        from app.services.groq_service import GroqService

        normalized = dict(data)
        for key in (
            "professional_summary",
            "skills_summary",
            "services_summary",
            "experience_summary",
        ):
            normalized[key] = GroqService._coerce_text_field(normalized.get(key))

        for key in ("skills", "experience", "education", "projects", "services", "tools", "technologies"):
            value = normalized.get(key)
            if value is None:
                normalized[key] = []
            elif not isinstance(value, list):
                normalized[key] = [value] if value else []

        name = normalized.get("name")
        if isinstance(name, str):
            normalized["name"] = name.strip() or None
        elif name is not None:
            normalized["name"] = str(name).strip() or None

        return normalized

    @staticmethod
    def _fallback_cv_profile(raw_text: str) -> tuple[dict, dict]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        name = lines[0][:120] if lines else None
        snippet = " ".join(lines[:8])[:500]
        return (
            {
                "name": name,
                "skills": [],
                "experience": [],
                "education": [],
                "projects": [],
                "services": [],
                "tools": [],
                "technologies": [],
            },
            {
                "professional_summary": snippet,
                "skills_summary": "",
                "services_summary": "",
                "experience_summary": "",
            },
        )

    def get_profile(self, user: User) -> CVProfileResponse | None:
        cv = self.cv_repository.get_latest_by_user(user.id)
        if not cv:
            return None
        return CVProfileResponse.model_validate(cv)

    def get_raw_text(self, user: User) -> CVRawResponse:
        cv = self.cv_repository.get_latest_by_user(user.id)
        if not cv or not cv.raw_text:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No CV raw text found. Please upload a CV first.",
            )
        return CVRawResponse(raw_text=cv.raw_text)
