"""Anti-bot detection: Cloudflare, CAPTCHA, rate limits."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class BotBlockType(str, Enum):
    none = "none"
    cloudflare = "cloudflare"
    captcha = "captcha"
    rate_limit = "rate_limit"
    access_denied = "access_denied"


@dataclass
class BotBlockResult:
    blocked: bool
    block_type: BotBlockType = BotBlockType.none
    should_retry: bool = False
    should_switch_proxy: bool = False
    should_use_browser: bool = False
    message: str = ""


_CLOUDFLARE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "cf-challenge",
    "checking your browser",
    "just a moment",
    "cloudflare",
    "ray id",
)

_CAPTCHA_MARKERS = (
    "g-recaptcha",
    "hcaptcha",
    "cf-turnstile",
    "captcha",
    "verify you are human",
    "are you a robot",
)

_RATE_LIMIT_MARKERS = (
    "too many requests",
    "rate limit",
    "429",
    "slow down",
    "try again later",
)


def detect_bot_block(
    html: str | None,
    *,
    status_code: int | None = None,
    headers: dict | None = None,
) -> BotBlockResult:
    if status_code == 429:
        return BotBlockResult(
            blocked=True,
            block_type=BotBlockType.rate_limit,
            should_retry=True,
            should_switch_proxy=True,
            message="HTTP 429 rate limited",
        )
    if status_code in (403, 503):
        return BotBlockResult(
            blocked=True,
            block_type=BotBlockType.access_denied,
            should_retry=True,
            should_switch_proxy=True,
            should_use_browser=True,
            message=f"HTTP {status_code} access denied",
        )

    headers = headers or {}
    server = str(headers.get("server", "")).lower()
    if "cloudflare" in server and status_code in (403, 503, None):
        return BotBlockResult(
            blocked=True,
            block_type=BotBlockType.cloudflare,
            should_retry=True,
            should_switch_proxy=True,
            should_use_browser=True,
            message="Cloudflare protection detected",
        )

    if not html:
        return BotBlockResult(blocked=False)

    low = html[:50_000].lower()

    if any(m in low for m in _CAPTCHA_MARKERS):
        return BotBlockResult(
            blocked=True,
            block_type=BotBlockType.captcha,
            should_retry=False,
            should_switch_proxy=True,
            message="CAPTCHA detected",
        )

    if any(m in low for m in _CLOUDFLARE_MARKERS):
        return BotBlockResult(
            blocked=True,
            block_type=BotBlockType.cloudflare,
            should_retry=True,
            should_switch_proxy=True,
            should_use_browser=True,
            message="Cloudflare challenge page",
        )

    if any(m in low for m in _RATE_LIMIT_MARKERS):
        return BotBlockResult(
            blocked=True,
            block_type=BotBlockType.rate_limit,
            should_retry=True,
            should_switch_proxy=True,
            message="Rate limit page detected",
        )

    if re.search(r"access\s+denied|forbidden|blocked", low) and len(low) < 8000:
        return BotBlockResult(
            blocked=True,
            block_type=BotBlockType.access_denied,
            should_retry=True,
            should_switch_proxy=True,
            message="Access denied page",
        )

    return BotBlockResult(blocked=False)
