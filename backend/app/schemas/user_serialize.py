"""Serialize User models with computed token fields."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserResponse
from app.services.token_quota_service import ensure_token_day, tokens_remaining


def to_user_response(user: User, db: Session | None = None) -> UserResponse:
    if db is not None:
        user = ensure_token_day(user, db)
    data = UserResponse.model_validate(user)
    remaining = tokens_remaining(user)
    # Unlimited for admin → expose high remaining for UI
    if remaining >= 10**8:
        remaining = -1
    return data.model_copy(update={"tokens_remaining": remaining})
