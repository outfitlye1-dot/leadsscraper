"""Detect low-resource hosts (Railway) and cap thread usage."""

from __future__ import annotations

import os


def is_constrained_host() -> bool:
    """Railway / small Docker hosts often hit OSError: can't start new thread."""
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_ID"):
        return True
    if (os.environ.get("ENVIRONMENT") or "").strip().lower() in {"production", "prod"}:
        return True
    return False


def constrained_worker_cap() -> int:
    """Hard ceiling for ThreadPoolExecutor size on small hosts."""
    return 1 if is_constrained_host() else 8
