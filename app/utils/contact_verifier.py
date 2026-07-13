import logging
from functools import lru_cache

from email_validator import EmailNotValidError, validate_email

from app.core.config import get_settings
from app.utils.contact_utils import _email_domain, is_junk_email, is_valid_email, score_email

logger = logging.getLogger(__name__)


@lru_cache(maxsize=512)
def domain_has_mx(domain: str) -> bool:
    if not domain:
        return False
    try:
        validate_email(f"probe@{domain}", check_deliverability=True)
        return True
    except EmailNotValidError:
        return False
    except Exception as exc:
        logger.debug("MX check failed for %s: %s", domain, exc)
        return False


def verify_email_deliverability(email: str, website: str | None = None) -> bool:
    """Format check always; MX check only when enabled and email is not high-confidence."""
    settings = get_settings()
    email = email.strip().lower()
    if not is_valid_email(email) or is_junk_email(email):
        return False

    if not settings.SCRAPER_VERIFY_EMAIL_MX:
        return True

    # High-confidence business emails: keep even if MX probe is slow/flaky
    if score_email(email, website) >= 40:
        return True

    domain = _email_domain(email)
    try:
        validate_email(email, check_deliverability=True)
        return True
    except EmailNotValidError:
        return domain_has_mx(domain)
    except Exception:
        return domain_has_mx(domain)
