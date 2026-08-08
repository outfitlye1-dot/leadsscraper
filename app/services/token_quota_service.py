"""Daily API token quota helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserPlan, UserRole


DEFAULT_FREE_DAILY_TOKENS = 50
DEFAULT_PAID_DAILY_TOKENS = 500


def utc_today() -> date:
    return datetime.now(UTC).date()


def ensure_token_day(user: User, db: Session) -> User:
    """Reset daily counter when the UTC day rolls over."""
    today = utc_today()
    if user.tokens_reset_on != today:
        user.tokens_used_today = 0
        user.tokens_reset_on = today
        db.commit()
        db.refresh(user)
    return user


def tokens_remaining(user: User) -> int:
    if user.role == UserRole.admin:
        return 10**9
    limit = max(0, int(user.daily_token_limit or 0))
    used = max(0, int(user.tokens_used_today or 0))
    return max(0, limit - used)


def usage_snapshot(user: User) -> dict:
    remaining = tokens_remaining(user)
    limit = int(user.daily_token_limit or 0)
    used = int(user.tokens_used_today or 0)
    if user.role == UserRole.admin:
        limit = 0
        used = 0
        remaining = -1  # unlimited sentinel for API consumers
    return {
        "plan": user.plan.value if hasattr(user.plan, "value") else str(user.plan),
        "daily_token_limit": limit,
        "tokens_used_today": used,
        "tokens_remaining": remaining,
        "tokens_reset_on": (user.tokens_reset_on or utc_today()).isoformat(),
        "api_access": bool(user.api_access) or user.role == UserRole.admin,
        "own_api_keys_enabled": bool(user.own_api_keys_enabled) or user.role == UserRole.admin,
        "own_api_keys_requested": bool(user.own_api_keys_requested),
        "paid_plan_requested": bool(getattr(user, "paid_plan_requested", False)),
        "is_unlimited": user.role == UserRole.admin,
        "paid_plan_tokens": DEFAULT_PAID_DAILY_TOKENS,
    }


def consume_tokens(db: Session, user_id: int, amount: int = 1) -> None:
    """Charge daily tokens after a successful platform API call. Admins skip."""
    if amount <= 0:
        return
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role == UserRole.admin:
        return

    user = ensure_token_day(user, db)

    if not user.api_access and not user.own_api_keys_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API access is disabled for your account. Ask an admin to enable it.",
        )

    remaining = tokens_remaining(user)
    if remaining < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Daily token limit reached ({user.daily_token_limit}/day). "
                "Upgrade to a paid plan or ask admin for more tokens / own API keys."
            ),
        )

    user.tokens_used_today = int(user.tokens_used_today or 0) + amount
    db.commit()


def require_tokens_available(db: Session, user_id: int, amount: int = 1) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == UserRole.admin:
        return user

    user = ensure_token_day(user, db)

    if not user.api_access and not user.own_api_keys_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API access is disabled for your account. Ask an admin to enable it.",
        )

    if tokens_remaining(user) < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Daily token limit reached ({user.daily_token_limit}/day). "
                "Upgrade to a paid plan or ask admin for more tokens / own API keys."
            ),
        )
    return user


def default_limit_for_plan(plan: UserPlan | str) -> int:
    value = plan.value if isinstance(plan, UserPlan) else str(plan)
    if value == UserPlan.paid.value:
        return DEFAULT_PAID_DAILY_TOKENS
    return DEFAULT_FREE_DAILY_TOKENS
