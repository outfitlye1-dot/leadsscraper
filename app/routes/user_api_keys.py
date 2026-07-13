from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.models.user_api_key import ApiProvider
from app.schemas.user_api_key import (
    UserApiKeyBulkCreateRequest,
    UserApiKeyBulkCreateResponse,
    UserApiKeyCreateRequest,
    UserApiKeyResponse,
    UserApiKeyUpdateRequest,
)
from app.services.user_api_key_service import UserApiKeyService

router = APIRouter(prefix="/api/user-keys", tags=["user-keys"])


@router.get(
    "",
    response_model=list[UserApiKeyResponse],
    summary="List your API keys (masked)",
)
def list_user_keys(
    provider: ApiProvider | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserApiKeyResponse]:
    return UserApiKeyService(db).list_keys(current_user, provider)


@router.post(
    "",
    response_model=UserApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add one API key",
)
def create_user_key(
    data: UserApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserApiKeyResponse:
    return UserApiKeyService(db).create_key(current_user, data)


@router.post(
    "/bulk",
    response_model=UserApiKeyBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add multiple API keys at once",
)
def bulk_create_user_keys(
    data: UserApiKeyBulkCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserApiKeyBulkCreateResponse:
    return UserApiKeyService(db).bulk_create(current_user, data)


@router.put(
    "/{key_id}",
    response_model=UserApiKeyResponse,
    summary="Update API key label, priority, or status",
)
def update_user_key(
    key_id: int,
    data: UserApiKeyUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserApiKeyResponse:
    return UserApiKeyService(db).update_key(current_user, key_id, data)


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an API key",
)
def delete_user_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    UserApiKeyService(db).delete_key(current_user, key_id)


@router.post(
    "/reset-exhausted",
    summary="Re-activate exhausted API keys",
)
def reset_exhausted_keys(
    provider: ApiProvider | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return UserApiKeyService(db).reset_exhausted(current_user, provider)
