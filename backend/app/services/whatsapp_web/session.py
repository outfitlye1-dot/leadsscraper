"""WhatsApp Web session helpers: login detect, QR capture, reconnect."""

from __future__ import annotations

import base64
import io
import logging
import re
import time
from typing import Any

from app.services.whatsapp_web.browser import wa_web_browser

logger = logging.getLogger(__name__)

# Resilient selectors — WhatsApp Web DOM changes often
_LOGGED_IN_SELECTORS = [
    "#pane-side",
    "#side",
    '[data-testid="chat-list"]',
    '[aria-label="Chat list"]',
    'div[aria-label="Chat list"]',
    '[data-testid="chat"]',
]

_QR_CANVAS_SELECTORS = [
    'div[data-ref] canvas',
    'canvas[aria-label*="QR" i]',
    'canvas[aria-label*="Scan" i]',
    '[data-testid="qrcode"] canvas',
    'div[data-testid="qrcode"] canvas',
]

_QR_CONTAINER_SELECTORS = [
    "div[data-ref]",
    '[data-testid="qrcode"]',
    'div[aria-label*="QR" i]',
]

_SHOW_QR_CLICK_TEXTS = [
    "Link with QR code",
    "Link a device",
    "Log in with WhatsApp Web",
    "QR code",
    "Scan QR code",
]


def _first_visible(page: Any, selectors: list[str], timeout_ms: int = 1500) -> Any | None:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            try:
                visible = loc.is_visible(timeout=timeout_ms)
            except TypeError:
                visible = loc.is_visible()
            if visible:
                return loc
        except Exception:
            continue
    return None


def _has_qr_markers(page: Any) -> bool:
    # Only treat *visible* QR as login screen — hidden data-ref nodes are common.
    return _first_visible(page, _QR_CANVAS_SELECTORS + _QR_CONTAINER_SELECTORS, timeout_ms=400) is not None


def _is_logged_in_on_page(page: Any) -> bool:
    """Detect chat UI even when Playwright locators flake on a CDP tab."""
    try:
        state = page.evaluate(
            """() => {
              const visible = (el) => {
                if (!el) return false;
                const r = el.getBoundingClientRect();
                return r.width > 8 && r.height > 8;
              };
              const qr = document.querySelector(
                'div[data-ref] canvas, [data-testid="qrcode"] canvas, canvas[aria-label*="QR" i]'
              );
              if (visible(qr)) return { loggedIn: false, reason: "qr" };
              const pane = document.querySelector(
                '#pane-side, #side, [data-testid="chat-list"], [aria-label="Chat list"]'
              );
              if (visible(pane)) return { loggedIn: true, reason: "pane" };
              const text = (document.body && document.body.innerText) || "";
              if (/end-to-end encrypted/i.test(text) && /Unread|Favorites|Groups/i.test(text)) {
                return { loggedIn: true, reason: "body" };
              }
              return { loggedIn: false, reason: "none" };
            }"""
        )
        if isinstance(state, dict) and state.get("loggedIn"):
            return True
        if isinstance(state, dict) and state.get("reason") == "qr":
            return False
    except Exception as exc:
        logger.debug("WA login evaluate failed: %s", exc)

    if _has_qr_markers(page):
        return False
    return _first_visible(page, _LOGGED_IN_SELECTORS, timeout_ms=2000) is not None


def is_logged_in(page: Any | None = None) -> bool:
    if page is not None and wa_web_browser.is_on_pw_thread():
        return _is_logged_in_on_page(page)
    if not wa_web_browser.is_started():
        return False
    return wa_web_browser.run(_is_logged_in_on_page, timeout=30.0)


def _click_show_qr_if_needed(page: Any) -> None:
    for text in _SHOW_QR_CLICK_TEXTS:
        try:
            btn = page.get_by_role("button", name=text)
            if btn.count() > 0 and btn.first.is_visible(timeout=600):
                btn.first.click(timeout=2000)
                time.sleep(0.8)
                return
        except Exception:
            pass
        try:
            link = page.get_by_text(text, exact=False)
            if link.count() > 0 and link.first.is_visible(timeout=400):
                link.first.click(timeout=2000)
                time.sleep(0.8)
                return
        except Exception:
            pass


def _png_from_data_ref(ref: str) -> bytes | None:
    ref = (ref or "").strip()
    if not ref or len(ref) < 20:
        return None
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except ImportError:
        logger.warning("qrcode package missing — pip install qrcode[pil]")
        return None
    try:
        qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=8, border=2)
        qr.add_data(ref)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Failed to render QR from data-ref: %s", exc)
        return None


def _read_data_ref(page: Any) -> str | None:
    for sel in ("div[data-ref]", "[data-ref]", 'div[data-testid="qrcode"]'):
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            ref = loc.get_attribute("data-ref")
            if ref and len(ref.strip()) > 20:
                return ref.strip()
        except Exception:
            continue
    return None


def _capture_qr_on_page(page: Any, wait_seconds: float) -> bytes | None:
    deadline = time.monotonic() + max(wait_seconds, 3.0)
    _click_show_qr_if_needed(page)
    if _is_logged_in_on_page(page):
        return None

    last_err: str | None = None
    while time.monotonic() < deadline:
        if _is_logged_in_on_page(page):
            return None
        _click_show_qr_if_needed(page)

        ref = _read_data_ref(page)
        if ref:
            png = _png_from_data_ref(ref)
            if png:
                logger.info("WA Web QR captured via data-ref (%s chars)", len(ref))
                return png

        canvas = _first_visible(page, _QR_CANVAS_SELECTORS, timeout_ms=700)
        if canvas is not None:
            try:
                png = canvas.screenshot(type="png")
                if png and len(png) > 500:
                    logger.info("WA Web QR captured via canvas screenshot")
                    return png
            except Exception as exc:
                last_err = str(exc)

        container = _first_visible(page, _QR_CONTAINER_SELECTORS, timeout_ms=500)
        if container is not None:
            try:
                png = container.screenshot(type="png")
                if png and len(png) > 500:
                    logger.info("WA Web QR captured via container screenshot")
                    return png
            except Exception as exc:
                last_err = str(exc)

        time.sleep(0.5)

    # Never return a page crop — Business phones show "Couldn't link" on non-QR images
    _ = last_err
    logger.warning("WA Web QR not found within %.0fs (url=%s)", wait_seconds, getattr(page, "url", ""))
    return None


def capture_qr_png_bytes(page: Any | None = None, wait_seconds: float = 25.0) -> bytes | None:
    """Return QR PNG bytes, or None if not shown / already logged in."""
    if page is not None and wa_web_browser.is_on_pw_thread():
        return _capture_qr_on_page(page, wait_seconds)
    return wa_web_browser.run(
        lambda p: _capture_qr_on_page(p, wait_seconds),
        timeout=max(60.0, wait_seconds + 30.0),
    )


def qr_png_to_data_url(png: bytes) -> str:
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"


def ensure_session(navigate: bool = True, settle_seconds: float = 2.5) -> dict[str, Any]:
    """Ensure browser is up, optionally open WhatsApp Web, report login state."""

    def _ensure(page: Any) -> dict[str, Any]:
        time.sleep(max(settle_seconds, 0.5))
        logged_in = _is_logged_in_on_page(page)
        # Never poke "Link device / QR" when chats are already visible — that
        # can yank a linked Business session back to the login screen.
        if not logged_in:
            _click_show_qr_if_needed(page)
            logged_in = _is_logged_in_on_page(page)
        logger.info(
            "WA Web ensure_session url=%s logged_in=%s cdp=%s",
            getattr(page, "url", None),
            logged_in,
            wa_web_browser.is_cdp_mode(),
        )
        return {
            "browser_started": True,
            "logged_in": logged_in,
            "profile_dir": str(wa_web_browser.profile_dir()),
            "page_url": getattr(page, "url", None),
            "cdp_mode": wa_web_browser.is_cdp_mode(),
        }

    if navigate:
        wa_web_browser.goto_whatsapp()
    else:
        wa_web_browser.ensure_started()
    return wa_web_browser.run(_ensure, timeout=90.0)


def reconnect() -> dict[str, Any]:
    """Close and relaunch persistent context, then open WhatsApp Web."""
    logger.info("WA Web reconnect requested")
    wa_web_browser.shutdown()
    return ensure_session(navigate=True)


def reset_session() -> dict[str, Any]:
    """Wipe saved browser profile and open a fresh WhatsApp Web login."""
    logger.info("WA Web reset session (clear profile)")
    wa_web_browser.reset_profile()
    return ensure_session(navigate=True)


def _visible_code_text(loc: Any) -> str:
    try:
        return (loc.inner_text(timeout=1500) or "").strip()
    except Exception:
        return ""


def _normalize_link_code(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    if len(cleaned) >= 8:
        return f"{cleaned[:4]}-{cleaned[4:8]}"
    return None


def _read_link_code(page: Any) -> str | None:
    selectors = [
        '[data-testid="link-with-phone-number-code-cells"]',
        "[data-link-code]",
        'div[data-link-code]',
        '[data-testid="link-device-phone-number-code"]',
        '[data-testid="link-device-phone-number-code-view"]',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            raw = loc.get_attribute("data-link-code") or _visible_code_text(loc)
            if raw and "," in raw:
                raw = raw.replace(",", "")
            code = _normalize_link_code(raw)
            if code:
                return code
        except Exception:
            continue
    try:
        text = page.locator("body").inner_text(timeout=2000) or ""
        m = re.search(r"\b([A-Z0-9]{4})\s*[-–]?\s*([A-Z0-9]{4})\b", text)
        if m:
            return _normalize_link_code(m.group(1) + m.group(2))
    except Exception:
        pass
    return None


def _split_phone(digits: str) -> tuple[str, str]:
    d = re.sub(r"\D", "", digits or "")
    if d.startswith("92") and len(d) >= 12:
        return "92", d[2:].lstrip("0") or d[2:]
    if d.startswith("91") and len(d) >= 12:
        return "91", d[2:].lstrip("0") or d[2:]
    if d.startswith("1") and len(d) == 11:
        return "1", d[1:]
    if len(d) > 10:
        return d[:-10], d[-10:]
    return "", d


def _click_link_with_phone(page: Any) -> bool:
    selectors = [
        '[data-testid="link-device-qrcode-alt-linking-hint"]',
        'button:has-text("Link with phone number")',
        'div[role="button"]:has-text("Link with phone number")',
        'span:has-text("Link with phone number")',
        'button:has-text("Log in with phone number")',
        'div[role="button"]:has-text("Log in with phone number")',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1200):
                loc.click(timeout=4000)
                time.sleep(1.2)
                return True
        except Exception:
            continue
    for text in ("Link with phone number", "Log in with phone number", "phone number instead"):
        try:
            loc = page.get_by_text(text, exact=False)
            if loc.count() > 0 and loc.first.is_visible(timeout=800):
                loc.first.click(timeout=4000)
                time.sleep(1.2)
                return True
        except Exception:
            continue
    return False


def _find_phone_input(page: Any) -> Any | None:
    selectors = [
        '[data-testid="link-device-phone-number-input"]',
        'input[aria-label*="phone" i]',
        'input[placeholder*="phone" i]',
        'input[type="tel"]',
        'form input[type="text"]',
        'input[type="text"]',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1500):
                return loc
        except Exception:
            continue
    return None


def _click_next(page: Any) -> bool:
    selectors = [
        '[data-testid="link-device-phone-number-entry-next-button"]',
        'button:has-text("Next")',
        'div[role="button"]:has-text("Next")',
        'button:has-text("Continue")',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1000):
                loc.click(timeout=4000)
                time.sleep(1.0)
                return True
        except Exception:
            continue
    try:
        btn = page.get_by_role("button", name=re.compile(r"next|continue", re.I))
        if btn.count() > 0 and btn.first.is_visible(timeout=800):
            btn.first.click(timeout=4000)
            time.sleep(1.0)
            return True
    except Exception:
        pass
    return False


def read_pair_code(wait_seconds: float = 25.0) -> dict[str, Any]:
    """Read pairing code already visible in the Chrome WhatsApp window."""

    def _read(page: Any) -> dict[str, Any]:
        if _is_logged_in_on_page(page):
            return {"logged_in": True, "pair_code": None, "message": "Already linked"}
        deadline = time.monotonic() + max(wait_seconds, 3.0)
        while time.monotonic() < deadline:
            code = _read_link_code(page)
            if code:
                return {
                    "logged_in": False,
                    "pair_code": code,
                    "message": (
                        "Code found. WhatsApp Business → Linked devices → Link a device → "
                        "Link with phone number → enter this code"
                    ),
                }
            time.sleep(0.5)
        raise RuntimeError(
            "No pair code on screen yet. Chrome window mein 'Link with phone number' click karo, "
            "number + Next, phir yahan 'Read code from Chrome' dubara dabao."
        )

    if not wa_web_browser.is_started():
        wa_web_browser.goto_whatsapp()
    return wa_web_browser.run(_read, timeout=max(60.0, wait_seconds + 20.0))


def request_pair_code(phone: str, wait_seconds: float = 25.0) -> dict[str, Any]:
    """Open 'Link with phone number' UI and return the 8-character pairing code."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 10:
        raise ValueError("Enter a valid WhatsApp Business number with country code (e.g. 923001234567)")
    dial, national = _split_phone(digits)

    def _pair(page: Any) -> dict[str, Any]:
        if _is_logged_in_on_page(page):
            return {
                "logged_in": True,
                "pair_code": None,
                "message": "Already linked",
            }

        existing = _read_link_code(page)
        if existing:
            return {
                "logged_in": False,
                "pair_code": existing,
                "phone": digits,
                "message": "Code already on screen — enter it in WhatsApp Business",
            }

        opened = _click_link_with_phone(page)
        time.sleep(0.8)
        phone_input = _find_phone_input(page)
        if phone_input is None and opened:
            time.sleep(1.5)
            phone_input = _find_phone_input(page)

        if phone_input is None:
            raise RuntimeError(
                "Phone box Chrome window mein open nahi hua. Wahan manually "
                "'Link with phone number' click karo, number enter + Next, phir yahan "
                "'Read code from Chrome' dabao."
            )

        try:
            phone_input.click(timeout=3000)
            time.sleep(0.2)
            try:
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
            except Exception:
                pass
            to_type = national or digits
            if dial == "92" and digits.startswith("92"):
                to_type = digits[2:]
            phone_input.type(to_type, delay=50)
        except Exception as exc:
            raise RuntimeError(f"Could not type phone number: {exc}") from exc

        _click_next(page)

        deadline = time.monotonic() + max(wait_seconds, 8.0)
        while time.monotonic() < deadline:
            if _is_logged_in_on_page(page):
                return {"logged_in": True, "pair_code": None, "message": "Linked"}
            code = _read_link_code(page)
            if code:
                return {
                    "logged_in": False,
                    "pair_code": code,
                    "phone": digits,
                    "message": (
                        "WhatsApp Business → Linked devices → Link a device → "
                        "Link with phone number → enter this code"
                    ),
                }
            time.sleep(0.6)

        raise RuntimeError(
            "Number fill ho gaya magar code nahi aaya. Chrome window check karo "
            "(Next dabao / country Pakistan), phir 'Read code from Chrome' try karo."
        )

    wa_web_browser.goto_whatsapp()
    return wa_web_browser.run(_pair, timeout=max(120.0, wait_seconds + 50.0))
