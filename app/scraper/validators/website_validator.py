"""Website URL validation."""

from urllib.parse import urlparse

from app.utils.website_utils import has_real_website


def validate_website(url: str | None) -> bool:
    return has_real_website(url)


def normalize_website_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def website_host(url: str | None) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""
