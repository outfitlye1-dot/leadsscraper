"""Disk-backed job checkpoints for crash recovery."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _checkpoint_dir() -> Path:
    base = Path(get_settings().EXPORT_DIR).parent / "checkpoints"
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_checkpoint(job_id: str, data: dict[str, Any]) -> None:
    path = _checkpoint_dir() / f"{job_id}.json"
    try:
        path.write_text(json.dumps(data, default=str), encoding="utf-8")
    except Exception as exc:
        logger.warning("Checkpoint save failed for %s: %s", job_id, exc)


def load_checkpoint(job_id: str) -> dict[str, Any] | None:
    path = _checkpoint_dir() / f"{job_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Checkpoint load failed for %s: %s", job_id, exc)
        return None


def delete_checkpoint(job_id: str) -> None:
    path = _checkpoint_dir() / f"{job_id}.json"
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
