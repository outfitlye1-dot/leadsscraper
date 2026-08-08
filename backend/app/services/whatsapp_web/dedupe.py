"""Dedupe helpers for WhatsApp Web inbound messages."""

from __future__ import annotations

import hashlib
import re


def normalize_phone_hint(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def make_dedupe_key(*, chat_title: str, body: str, phone_hint: str | None = None) -> str:
    title = (chat_title or "").strip().lower()[:120]
    text = (body or "").strip().lower()[:500]
    phone = normalize_phone_hint(phone_hint)
    raw = f"{phone}|{title}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]
