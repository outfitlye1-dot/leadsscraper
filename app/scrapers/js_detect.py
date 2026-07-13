"""Detect pages that need a JavaScript renderer (Playwright) instead of plain HTTP."""

from __future__ import annotations

from bs4 import BeautifulSoup

MIN_USEFUL_HTML_LENGTH = 400

JS_SHELL_MARKERS = (
    "enable javascript",
    "javascript is required",
    "please enable js",
    "you need to enable javascript",
    "this site requires javascript",
    "javascript is disabled",
    "requires javascript",
    "without javascript",
)

SPA_ROOT_IDS = ("root", "app", "__next", "___gatsby", "main-content")


def _visible_text_length(html: str) -> int:
    try:
        soup = BeautifulSoup(html, "lxml")
        body = soup.find("body")
        if not body:
            return len(soup.get_text(strip=True))
        return len(body.get_text(strip=True))
    except Exception:
        return 0


def _script_count(html: str) -> int:
    try:
        return len(BeautifulSoup(html, "lxml").find_all("script"))
    except Exception:
        return html.lower().count("<script")


def looks_like_js_shell(html: str) -> bool:
    """True when HTML is likely a JS app shell without rendered business content."""
    if not html or not html.strip():
        return True

    lower = html.lower()
    if any(marker in lower for marker in JS_SHELL_MARKERS):
        return True

    text_len = _visible_text_length(html)
    scripts = _script_count(html)

    if scripts >= 2 and text_len < 150:
        return True

    if "__next_data__" in lower or "window.__nuxt__" in lower or "data-reactroot" in lower:
        if text_len < 220:
            return True

    try:
        soup = BeautifulSoup(html, "lxml")
        for root_id in SPA_ROOT_IDS:
            node = soup.find(id=root_id)
            if node and len(node.get_text(strip=True)) < 40 and scripts >= 1:
                return True
    except Exception:
        pass

    if len(html) < MIN_USEFUL_HTML_LENGTH and scripts >= 1:
        return True

    return False


def is_useful_html(html: str) -> bool:
    """True when static HTML is rich enough to parse contacts without JS render."""
    if not html or len(html) < MIN_USEFUL_HTML_LENGTH:
        return False
    if looks_like_js_shell(html):
        return False
    return True
