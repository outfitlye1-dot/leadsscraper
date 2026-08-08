"""Comprehensive email verification before outreach."""

from __future__ import annotations

from dataclasses import dataclass, asdict

from email_validator import EmailNotValidError, validate_email

from app.utils.contact_utils import _email_domain, is_junk_email, is_valid_email, score_email
from app.utils.contact_verifier import domain_has_mx

DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "guerrillamail.com",
    "tempmail.com",
    "10minutemail.com",
    "throwaway.email",
    "yopmail.com",
    "trashmail.com",
    "getnada.com",
    "sharklasers.com",
    "dispostable.com",
    "maildrop.cc",
    "fakeinbox.com",
}


@dataclass
class EmailVerificationResult:
    email: str
    is_valid: bool
    is_verified: bool
    is_risky: bool
    is_disposable: bool
    has_mx: bool
    syntax_valid: bool
    domain_valid: bool
    score: int
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def verify_outreach_email(email: str | None, website: str | None = None) -> EmailVerificationResult:
    reasons: list[str] = []
    if not email or not str(email).strip():
        return EmailVerificationResult(
            email=email or "",
            is_valid=False,
            is_verified=False,
            is_risky=True,
            is_disposable=False,
            has_mx=False,
            syntax_valid=False,
            domain_valid=False,
            score=0,
            reasons=["missing_email"],
        )

    normalized = email.strip().lower()
    syntax_valid = is_valid_email(normalized)
    if not syntax_valid:
        return EmailVerificationResult(
            email=normalized,
            is_valid=False,
            is_verified=False,
            is_risky=True,
            is_disposable=False,
            has_mx=False,
            syntax_valid=False,
            domain_valid=False,
            score=0,
            reasons=["invalid_syntax"],
        )

    domain = _email_domain(normalized)
    domain_valid = bool(domain and "." in domain)
    is_disposable = domain in DISPOSABLE_DOMAINS or any(
        domain.endswith(f".{d}") for d in DISPOSABLE_DOMAINS
    )
    if is_disposable:
        reasons.append("disposable_provider")
    if is_junk_email(normalized):
        reasons.append("junk_email")

    has_mx = False
    try:
        validate_email(normalized, check_deliverability=True)
        has_mx = True
    except EmailNotValidError:
        has_mx = domain_has_mx(domain)
        if not has_mx:
            reasons.append("no_mx_records")
    except Exception:
        has_mx = domain_has_mx(domain)
        if not has_mx:
            reasons.append("mx_check_failed")

    email_score = score_email(normalized, website)
    is_risky = bool(reasons) or email_score < 20
    if email_score < 20 and "low_confidence" not in reasons:
        reasons.append("low_confidence")

    is_verified = (
        syntax_valid
        and domain_valid
        and has_mx
        and not is_disposable
        and not is_junk_email(normalized)
        and email_score >= 20
    )

    return EmailVerificationResult(
        email=normalized,
        is_valid=syntax_valid and domain_valid,
        is_verified=is_verified,
        is_risky=is_risky,
        is_disposable=is_disposable,
        has_mx=has_mx,
        syntax_valid=syntax_valid,
        domain_valid=domain_valid,
        score=email_score,
        reasons=reasons,
    )


def can_send_to_email(result: EmailVerificationResult) -> bool:
    return result.is_verified and not result.is_disposable and not result.is_risky
