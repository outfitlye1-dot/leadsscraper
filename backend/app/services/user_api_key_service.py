from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.user_api_key import ApiKeyStatus, ApiProvider
from app.repositories.user_api_key_repository import UserApiKeyRepository
from app.schemas.user_api_key import (
    UserApiKeyBulkCreateRequest,
    UserApiKeyBulkCreateResponse,
    UserApiKeyCreateRequest,
    UserApiKeyResponse,
    UserApiKeyUpdateRequest,
)
from app.utils.api_key_utils import mask_api_key


class UserApiKeyService:
    def __init__(self, db: Session):
        self.repo = UserApiKeyRepository(db)

    def _scope(self, user: User) -> str:
        """platform = admin shared pool; own = user keys."""
        if user.role == UserRole.admin:
            return "platform"
        if user.own_api_keys_enabled:
            return "own"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You cannot manage API keys. Ask an admin to approve own-API access, "
                "or use your daily platform tokens."
            ),
        )

    def _to_response(self, row) -> UserApiKeyResponse:
        data = {
            "id": row.id,
            "provider": row.provider,
            "label": row.label,
            "masked_key": mask_api_key(row.api_key),
            "priority": row.priority,
            "status": row.status,
            "usage_count": row.usage_count,
            "last_error": row.last_error,
            "last_used_at": row.last_used_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        return UserApiKeyResponse(**data)

    def list_keys(self, user: User, provider: ApiProvider | None = None) -> list[UserApiKeyResponse]:
        scope = self._scope(user)
        if scope == "platform":
            rows = self.repo.list_platform_keys(provider)
        else:
            rows = self.repo.list_by_user(user.id, provider)
        return [self._to_response(r) for r in rows]

    def create_key(self, user: User, data: UserApiKeyCreateRequest) -> UserApiKeyResponse:
        self._scope(user)
        api_key = data.api_key.strip()
        if len(api_key) < 8:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key too short")

        row = self.repo.create(
            user.id,
            {
                "provider": data.provider,
                "label": data.label.strip() or "API Key",
                "api_key": api_key,
                "priority": self.repo.next_priority(user.id, data.provider),
                "status": ApiKeyStatus.active,
            },
        )
        return self._to_response(row)

    def bulk_create(self, user: User, data: UserApiKeyBulkCreateRequest) -> UserApiKeyBulkCreateResponse:
        self._scope(user)
        cleaned = []
        seen: set[str] = set()
        for raw in data.api_keys:
            key = raw.strip()
            if len(key) < 8 or key in seen:
                continue
            seen.add(key)
            cleaned.append(key)

        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid API keys provided (minimum 8 characters each).",
            )

        start_priority = self.repo.next_priority(user.id, data.provider)
        rows_data = []
        for idx, key in enumerate(cleaned):
            rows_data.append(
                {
                    "provider": data.provider,
                    "label": f"{data.label_prefix.strip()} {start_priority + idx + 1}",
                    "api_key": key,
                    "priority": start_priority + idx,
                    "status": ApiKeyStatus.active,
                }
            )

        created_rows = self.repo.bulk_create(user.id, rows_data)
        return UserApiKeyBulkCreateResponse(
            created=len(created_rows),
            keys=[self._to_response(r) for r in created_rows],
        )

    def update_key(
        self, user: User, key_id: int, data: UserApiKeyUpdateRequest
    ) -> UserApiKeyResponse:
        scope = self._scope(user)
        if scope == "platform":
            row = self.repo.get_platform_key_by_id(key_id)
        else:
            row = self.repo.get_by_id(user.id, key_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        updated = self.repo.update(row, data.model_dump(exclude_unset=True))
        return self._to_response(updated)

    def delete_key(self, user: User, key_id: int) -> None:
        scope = self._scope(user)
        if scope == "platform":
            row = self.repo.get_platform_key_by_id(key_id)
        else:
            row = self.repo.get_by_id(user.id, key_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        self.repo.delete(row)

    def reset_exhausted(self, user: User, provider: ApiProvider | None = None) -> dict:
        scope = self._scope(user)
        if scope == "platform":
            count = self.repo.reset_exhausted_platform(provider)
        else:
            count = self.repo.reset_exhausted(user.id, provider)
        return {"reset_count": count}
