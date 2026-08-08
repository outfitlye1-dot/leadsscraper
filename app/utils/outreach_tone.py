"""Paid-service outreach rules — customer messages must never offer free work."""

from __future__ import annotations

import re
from typing import Any

# Defaults when Brain pricing is not set
CLIENT_OFFER_MIN_USD = 300
CLIENT_OFFER_MAX_USD = 1000


def _fmt_money(amount: float, currency: str) -> str:
    currency = (currency or "USD").strip().upper() or "USD"
    if amount == int(amount):
        return f"{currency} {int(amount):,}"
    return f"{currency} {amount:,.2f}"


def resolve_pricing(
    *,
    pricing_high: float | None = None,
    pricing_floor: float | None = None,
    pricing_currency: str | None = None,
) -> tuple[float, float, str]:
    """Return (high/opening, floor/minimum, currency)."""
    currency = (pricing_currency or "USD").strip().upper() or "USD"
    high = float(pricing_high) if pricing_high is not None and pricing_high > 0 else float(
        CLIENT_OFFER_MAX_USD
    )
    floor = (
        float(pricing_floor)
        if pricing_floor is not None and pricing_floor > 0
        else float(CLIENT_OFFER_MIN_USD)
    )
    if high < floor:
        high, floor = floor, high
    return high, floor, currency


def resolve_pricing_from_brain(brain: Any | None) -> tuple[float, float, str]:
    if brain is None:
        return resolve_pricing()
    return resolve_pricing(
        pricing_high=getattr(brain, "pricing_high", None),
        pricing_floor=getattr(brain, "pricing_floor", None),
        pricing_currency=getattr(brain, "pricing_currency", None),
    )


def build_pricing_rules(
    *,
    pricing_high: float | None = None,
    pricing_floor: float | None = None,
    pricing_currency: str | None = None,
) -> str:
    high, floor, currency = resolve_pricing(
        pricing_high=pricing_high,
        pricing_floor=pricing_floor,
        pricing_currency=pricing_currency,
    )
    mid = (high + floor) / 2
    high_s = _fmt_money(high, currency)
    mid_s = _fmt_money(mid, currency)
    floor_s = _fmt_money(floor, currency)
    return f"""
DEAL / PRICING (Brain — follow exactly — REPLIES ONLY):
- Opening HIGH quote (ONLY when they first ask price / cost / package, and you have NOT quoted yet): {high_s}
- Mid negotiation target: around {mid_s}
- Floor / never go below: {floor_s}
- Goal: CLOSE A DEAL like a real human salesperson — warm, clear, no robot tone.

WHEN TO QUOTE:
- First cold message / intro: NEVER mention any number or package price.
- Only quote when they ask (price, cost, kitna, fees, package, budget) OR clearly want to buy.

NEGOTIATION / PACKAGE AUTO-ADJUST:
  1) First price ask → open at HIGH ({high_s}) and briefly say what that package covers.
  2) If they say "ok" / "sounds good" / "let's do it" → confirm the deal at the last number you quoted, ask a simple next step (pay / details / start).
  3) If they say "less" / "too expensive" / "discount" / give a lower number → auto-adjust the package (smaller scope / fewer pages / basic package) and counter toward mid ({mid_s}), still >= {floor_s}. Explain the adjusted scope in one short line.
  4) If YOU already gave a lower/mid number in history → never jump back to HIGH. Continue from that last offer.
  5) If their budget >= floor → accept or counter slightly above, then lock.
  6) If their offer is below floor → hold floor and ask what smaller scope fits {floor_s}.
  7) NEVER restart the pitch. Never repeat the same price sentence. Never invent free work.

HUMAN TOUCH ON PRICE REPLIES:
- Sound like a person texting a client: "Sure — for a solid package it's about {high_s}." / "I can do a lighter version around {mid_s} if we keep scope simple."
- 1–3 short sentences. Contractions English (I'll, you're, that's).
- Match their energy: short reply if they were short; warmer if they were friendly.
""".strip()


def build_pricing_snippet(
    *,
    pricing_high: float | None = None,
    pricing_floor: float | None = None,
    pricing_currency: str | None = None,
) -> str:
    high, floor, currency = resolve_pricing(
        pricing_high=pricing_high,
        pricing_floor=pricing_floor,
        pricing_currency=pricing_currency,
    )
    return (
        f"Professional packages typically {_fmt_money(floor, currency)}–"
        f"{_fmt_money(high, currency)}, depending on what you need."
    )


def build_pricing_rules_for_user(db, user_id: int) -> str:
    from app.repositories.brain_repository import BrainRepository

    brain = BrainRepository(db).get_by_user(user_id)
    high, floor, currency = resolve_pricing_from_brain(brain)
    return build_pricing_rules(
        pricing_high=high, pricing_floor=floor, pricing_currency=currency
    )


# Backward-compatible defaults (used when no user context)
CLIENT_PRICING_RULES = build_pricing_rules()
CLIENT_PRICING_SNIPPET = build_pricing_snippet()

# First cold outreach — introduce work only; never quote numbers
FIRST_MESSAGE_OUTREACH_RULES = """
FIRST MESSAGE RULES (critical):
- Address them respectfully as "sir" (e.g. "Hi sir," / "Hello sir,") — even if you only have a phone number and no personal name. This shows respect.
- If a real first name is known, you may use "Hi {name} sir," or just "Hi sir," — prefer "sir" for respect on first contact
- Do NOT use "there", "friend", "buddy", or unnamed "Hi," alone
- ONLY introduce who you are and what work you do for local businesses like theirs
- Do NOT mention any price, fee, package cost, discount, or number
- Do NOT auto-adjust packages in the first message
- Soft CTA: ask if they'd like to chat / hear how you can help — pricing comes later when THEY ask
- This is paid professional work — never offer free quotes, trials, audits, or free work
- Forbidden words: free, complimentary, no cost, pro bono, free trial, free quote, free audit, free consultation
"""

# Kept for older imports; first-message prompts should use FIRST_MESSAGE_OUTREACH_RULES
PAID_SERVICE_OUTREACH_RULES = FIRST_MESSAGE_OUTREACH_RULES

HUMAN_TOUCH_OUTREACH_RULES = """
HUMAN TOUCH (sound like a real person, not a bot):
- Warm, natural, casual-professional — like messaging a local business owner you respect
- Short sentences. No long paragraphs, bullet lists, or multiple pitches
- Use contractions: I'll, you're, that's, we're
- Open with respect: "Hi sir," is preferred on first WhatsApp/message (not "Dear Sir/Madam", not "Hi there")
- Avoid stiff openers: "I hope this finds you well", "I am reaching out to"
- Avoid buzzwords: leverage, synergy, cutting-edge, innovative solutions, digital landscape
- Use their business name once, naturally — not every sentence
- Light personality OK; never sound scripted or template-y
- WhatsApp / chat: sometimes 0–1 friendly emoji (not every message). First cold email: usually no emoji
"""

OUTREACH_MAX_CHARS = {
    "whatsapp": 200,
    "linkedin": 250,
    "follow_up": 220,
    "email_subject": 55,
    "email_body": 480,
    "email_cta": 80,
}

_FREE_PHRASE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bfree\s+quote\b", re.I), "a quote"),
    (re.compile(r"\bfree\s+consultation\b", re.I), "a consultation"),
    (re.compile(r"\bfree\s+audit\b", re.I), "a website review"),
    (re.compile(r"\bfree\s+trial\b", re.I), "a paid starter package"),
    (re.compile(r"\bfree\s+website\b", re.I), "a professional website"),
    (re.compile(r"\bfor\s+free\b", re.I), "as part of our paid service"),
    (re.compile(r"\bfree\s+of\s+charge\b", re.I), "with clear pricing"),
    (re.compile(r"\bat\s+no\s+cost\b", re.I), "with transparent pricing"),
    (re.compile(r"\bno\s+cost\b", re.I), "paid"),
    (re.compile(r"\bcomplimentary\b", re.I), "professional"),
    (re.compile(r"\bpro\s+bono\b", re.I), "professional"),
)


def sanitize_paid_outreach_message(text: str) -> str:
    """Remove/rephrase 'free' hooks from customer-facing outreach copy."""
    if not text:
        return text
    result = text
    for pattern, replacement in _FREE_PHRASE_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    result = re.sub(r"\bfree\b", "", result, flags=re.I)
    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"\s+([,.!?])", r"\1", result)
    return result.strip()


def trim_outreach_message(text: str, max_chars: int) -> str:
    """Trim outreach copy at a sentence boundary when possible."""
    text = text.strip()
    if len(text) <= max_chars:
        return text

    chunk = text[:max_chars]
    for sep in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
        idx = chunk.rfind(sep)
        if idx >= int(max_chars * 0.45):
            return chunk[: idx + len(sep.rstrip())].strip()

    trimmed = chunk.rstrip()
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    return trimmed.rstrip(".,;:-") + "..."
