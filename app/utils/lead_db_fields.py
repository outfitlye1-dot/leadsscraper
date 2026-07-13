"""Filter lead dicts to valid SQLAlchemy Lead columns before insert/update."""

from __future__ import annotations

from sqlalchemy import inspect

from app.models.lead import Lead

_LEAD_COLUMNS: set[str] | None = None


def lead_column_names() -> set[str]:
    global _LEAD_COLUMNS
    if _LEAD_COLUMNS is None:
        _LEAD_COLUMNS = {attr.key for attr in inspect(Lead).mapper.column_attrs}
    return _LEAD_COLUMNS


def strip_lead_dict(data: dict) -> dict:
    allowed = lead_column_names()
    return {k: v for k, v in data.items() if k in allowed}
