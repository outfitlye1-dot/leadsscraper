"""Paid-service outreach rules — customer messages must never offer free work."""

from __future__ import annotations

import re

# Client-facing package range (USD) — used in WhatsApp, email, LinkedIn, and AI outreach.
CLIENT_OFFER_MIN_USD = 300
CLIENT_OFFER_MAX_USD = 1000

CLIENT_PRICING_RULES = f"""
- Service packages start from ${CLIENT_OFFER_MIN_USD} and typically range up to ${CLIENT_OFFER_MAX_USD} depending on scope
- You may mention this price range naturally when relevant (e.g. "packages from ${CLIENT_OFFER_MIN_USD}" or "${CLIENT_OFFER_MIN_USD}–${CLIENT_OFFER_MAX_USD}")
- Do NOT quote below ${CLIENT_OFFER_MIN_USD} or above ${CLIENT_OFFER_MAX_USD} unless the lead explicitly asks for a custom enterprise scope
- Do NOT say "free", "cheap", or "budget" — position as professional paid packages
"""

CLIENT_PRICING_SNIPPET = (
    f"Professional packages from ${CLIENT_OFFER_MIN_USD} to ${CLIENT_OFFER_MAX_USD}, "
    "depending on what you need."
)

PAID_SERVICE_OUTREACH_RULES = """
- This is a PAID professional service — never offer anything free
- Do NOT use: free, complimentary, no cost, no charge, pro bono, free trial, free quote, free audit, free consultation, free sample, or "at no obligation"
- Do NOT imply discounts or giveaways to hook the lead
- Present paid value: professional packages, quality work, fair pricing — invite them to discuss requirements and pricing
""" + CLIENT_PRICING_RULES

HUMAN_TOUCH_OUTREACH_RULES = """
- Sound like a real person — warm, casual-professional, not corporate or salesy
- Short sentences only. No long paragraphs, bullet lists, or multiple pitches
- One simple idea: quick hello + why you messaged + soft question or CTA
- Avoid stiff openers: "I hope this finds you well", "I am reaching out to", "Dear Sir/Madam"
- Avoid buzzwords: leverage, synergy, cutting-edge, innovative solutions, digital landscape
- Use the lead's name or business name once, naturally
- WhatsApp: 0-1 emoji max (optional). LinkedIn/email: no emojis
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
