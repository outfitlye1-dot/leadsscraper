"""Detect API quota / rate-limit errors for key rotation."""

from fastapi import HTTPException

QUOTA_HINTS = (
    "limit",
    "quota",
    "exceeded",
    "rate",
    "429",
    "402",
    "billing",
    "credit",
    "usage",
    "too many",
    "insufficient",
    "exhausted",
    "monthly",
)

TRANSIENT_HINTS = (
    "connection",
    "timeout",
    "timed out",
    "network",
    "connect",
    "unreachable",
    "temporarily",
    "503",
    "502",
    "504",
)


def is_quota_or_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(hint in message for hint in QUOTA_HINTS)


def is_transient_api_error(exc: Exception) -> bool:
    message = str(exc).lower()
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        message = f"{message} {detail}".lower()
    return any(hint in message for hint in TRANSIENT_HINTS)


def mask_api_key(api_key: str) -> str:
    key = (api_key or "").strip()
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"
