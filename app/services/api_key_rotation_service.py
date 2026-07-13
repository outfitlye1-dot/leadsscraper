from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user_api_key import ApiProvider
from app.repositories.user_api_key_repository import UserApiKeyRepository
from app.utils.api_key_utils import is_quota_or_limit_error, is_transient_api_error

T = TypeVar("T")


class ApiKeyRotationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserApiKeyRepository(db)

    def get_user_tokens(self, user_id: int, provider: ApiProvider) -> list[str]:
        keys = self.repo.get_active_keys(user_id, provider)
        return [k.api_key for k in keys]

    def execute_with_rotation(
        self,
        user_id: int,
        provider: ApiProvider,
        operation: Callable[[str], T],
    ) -> T:
        keys = self.repo.get_active_keys(user_id, provider)
        errors: list[str] = []

        for key_row in keys:
            try:
                result = operation(key_row.api_key)
                self.repo.record_success(key_row)
                return result
            except Exception as exc:
                error_text = str(exc)
                errors.append(error_text)
                if is_quota_or_limit_error(exc):
                    self.repo.mark_exhausted(key_row, error_text)
                    continue
                if is_transient_api_error(exc):
                    continue
                raise

        provider_name = provider.value.upper()
        if errors:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"All your {provider_name} API keys failed or hit their limit. "
                    f"Add new keys in Settings → API Keys. Last error: {errors[-1][:200]}"
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No {provider_name} API key found for your account. "
                "Add your own key in Settings → API Keys."
            ),
        )
