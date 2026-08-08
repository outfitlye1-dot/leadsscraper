from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.user_api_key import ApiProvider
from app.repositories.user_api_key_repository import UserApiKeyRepository
from app.services.token_quota_service import consume_tokens, require_tokens_available
from app.utils.api_key_utils import is_quota_or_limit_error, is_transient_api_error

T = TypeVar("T")


class ApiKeyRotationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserApiKeyRepository(db)

    def _get_user(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def _keys_for_user(self, user: User, provider: ApiProvider):
        """Own keys (if allowed) first, then shared platform keys."""
        keys = []
        if user.role == UserRole.admin or user.own_api_keys_enabled:
            keys.extend(self.repo.get_active_keys(user.id, provider))
        if user.role == UserRole.admin or user.api_access:
            platform = self.repo.get_active_platform_keys(provider)
            seen = {k.id for k in keys}
            for row in platform:
                if row.id not in seen:
                    keys.append(row)
        return keys

    def _is_platform_key(self, key_row) -> bool:
        owner = self._get_user(key_row.user_id)
        return bool(owner and owner.role == UserRole.admin)

    def get_user_tokens(self, user_id: int, provider: ApiProvider) -> list[str]:
        user = self._get_user(user_id)
        if not user:
            return []
        keys = self._keys_for_user(user, provider)
        if not keys:
            return []
        has_own = any(not self._is_platform_key(k) for k in keys)
        if not has_own and user.role != UserRole.admin:
            require_tokens_available(self.db, user_id, amount=1)
        return [k.api_key for k in keys]

    def execute_with_rotation(
        self,
        user_id: int,
        provider: ApiProvider,
        operation: Callable[[str], T],
        *,
        token_cost: int = 1,
    ) -> T:
        user = self._get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        keys = self._keys_for_user(user, provider)
        provider_name = provider.value.upper()
        if not keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"No {provider_name} API key available. "
                    "Ask an admin to add platform keys or approve your own API keys."
                ),
            )

        has_own = any(not self._is_platform_key(k) for k in keys)
        has_platform = any(self._is_platform_key(k) for k in keys)
        if has_platform and not has_own and user.role != UserRole.admin:
            require_tokens_available(self.db, user_id, amount=token_cost)

        errors: list[str] = []

        for key_row in keys:
            is_platform = self._is_platform_key(key_row)
            if is_platform and user.role != UserRole.admin:
                try:
                    require_tokens_available(self.db, user_id, amount=token_cost)
                except HTTPException as exc:
                    errors.append(str(exc.detail))
                    continue
            try:
                result = operation(key_row.api_key)
                self.repo.record_success(key_row)
                # Platform keys burn daily tokens; own keys do not.
                if is_platform and user.role != UserRole.admin:
                    consume_tokens(self.db, user_id, token_cost)
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

        if errors:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"All {provider_name} API keys failed or hit their limit. "
                    f"Ask an admin to add keys, or use your own API keys. Last error: {errors[-1][:200]}"
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No {provider_name} API key available. "
                "Ask an admin to add platform keys or approve your own API keys."
            ),
        )
