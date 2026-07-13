"""Timezone helpers for SQLite datetime values (often stored/read as naive UTC)."""

from __future__ import annotations

from datetime import UTC, datetime


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
