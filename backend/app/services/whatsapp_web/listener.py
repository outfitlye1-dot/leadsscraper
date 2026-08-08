"""Detect new unread WhatsApp Web chats and enqueue inbound texts (no AI send here)."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from app.services.whatsapp_web.browser import wa_web_browser

logger = logging.getLogger(__name__)

_UNREAD_ROW_SELECTORS = [
    '#pane-side span[aria-label*="unread message"]',
    '#pane-side span[aria-label*="unread"]',
    '[data-testid="icon-unread-count"]',
]

_CHAT_ROW_SELECTORS = [
    '#pane-side div[role="listitem"]',
    '#pane-side div[role="row"]',
]

_HEADER_TITLE_SELECTORS = [
    'header span[dir="auto"]',
    'header [data-testid="conversation-info-header-chat-title"]',
    "#main header span[title]",
]

_INCOMING_MSG_SELECTORS = [
    'div.message-in span.selectable-text',
    'div[data-testid="msg-container"] span.selectable-text',
]


def _visible_text(loc: Any) -> str:
    try:
        return (loc.inner_text(timeout=1500) or "").strip()
    except Exception:
        return ""


def _phone_from_title(title: str) -> str | None:
    digits = re.sub(r"\D", "", title or "")
    if len(digits) >= 10:
        return digits
    return None


def _phone_from_page(page: Any) -> str | None:
    """Extract WhatsApp chat phone from message data-id / tel links."""
    try:
        phone = page.evaluate(
            """() => {
              const pick = (raw) => {
                if (!raw) return null;
                const m = String(raw).match(/(\\d{10,15})/);
                return m ? m[1] : null;
              };
              const nodes = Array.from(document.querySelectorAll('[data-id]'));
              for (let i = nodes.length - 1; i >= 0; i--) {
                const id = nodes[i].getAttribute('data-id') || '';
                // true_923001234567@c.us_ABCDEF or 92300...@c.us
                let m = id.match(/(?:true|false)_(\\d{10,15})@c\\.us/i);
                if (m) return m[1];
                m = id.match(/(\\d{10,15})@c\\.us/i);
                if (m) return m[1];
              }
              const tel = document.querySelector('a[href^="tel:"]');
              if (tel) {
                const p = pick(tel.getAttribute('href'));
                if (p) return p;
              }
              const title = document.querySelector('#main header span[title], header [data-testid="conversation-info-header-chat-title"]');
              if (title) {
                const p = pick(title.getAttribute('title') || title.textContent || '');
                if (p) return p;
              }
              return null;
            }"""
        )
        if phone and len(re.sub(r"\D", "", str(phone))) >= 10:
            return re.sub(r"\D", "", str(phone))
    except Exception as exc:
        logger.debug("WA Web phone extract failed: %s", exc)
    return None


def _looks_like_group(title: str) -> bool:
    t = (title or "").lower()
    return any(x in t for x in ("group", "community", "broadcast"))


def poll_unread_and_collect(max_chats: int = 5) -> list[dict[str, str]]:
    """Open unread chats, read latest inbound text, return list of {chat_title, body, phone_hint}."""
    if not wa_web_browser.is_started():
        return []

    def _poll(page: Any) -> list[dict[str, str]]:
        from app.services.whatsapp_web.session import _is_logged_in_on_page

        results: list[dict[str, str]] = []
        if not _is_logged_in_on_page(page):
            logger.debug("WA Web listener: not logged in")
            return results

        # Prefer rows that contain an unread badge
        candidates: list[Any] = []
        for sel in _CHAT_ROW_SELECTORS:
            try:
                rows = page.locator(sel)
                count = min(rows.count(), 40)
                for i in range(count):
                    row = rows.nth(i)
                    try:
                        if not row.is_visible(timeout=300):
                            continue
                    except Exception:
                        continue
                    unread = False
                    for u_sel in _UNREAD_ROW_SELECTORS:
                        try:
                            if row.locator(u_sel).count() > 0:
                                unread = True
                                break
                        except Exception:
                            continue
                    try:
                        aria = row.inner_text(timeout=400) or ""
                        if re.search(r"\bunread\b", aria, re.I):
                            unread = True
                    except Exception:
                        pass
                    if unread:
                        candidates.append(row)
                if candidates:
                    break
            except Exception as exc:
                logger.debug("WA Web chat row scan failed (%s): %s", sel, exc)

        for row in candidates[: max(1, max_chats)]:
            try:
                row.click(timeout=3000)
                time.sleep(0.8)
            except Exception as exc:
                logger.debug("WA Web open chat failed: %s", exc)
                continue

            title = ""
            for hsel in _HEADER_TITLE_SELECTORS:
                try:
                    loc = page.locator(hsel).first
                    if loc.count() > 0:
                        title = (loc.get_attribute("title") or _visible_text(loc) or "").strip()
                        if title:
                            break
                except Exception:
                    continue
            if not title:
                title = "unknown"

            body = ""
            for msel in _INCOMING_MSG_SELECTORS:
                try:
                    msgs = page.locator(msel)
                    n = msgs.count()
                    if n <= 0:
                        continue
                    if "message-in" in msel:
                        body = _visible_text(msgs.nth(n - 1))
                    else:
                        for j in range(n - 1, max(-1, n - 8), -1):
                            node = msgs.nth(j)
                            try:
                                parent_html = node.evaluate(
                                    """el => {
                                      let p = el.closest('div.message-out, div.message-in, div[data-testid="msg-container"]');
                                      return p ? p.className + ' ' + (p.getAttribute('data-testid')||'') : '';
                                    }"""
                                )
                            except Exception:
                                parent_html = ""
                            if "message-out" in (parent_html or ""):
                                continue
                            body = _visible_text(node)
                            if body:
                                break
                    if body:
                        break
                except Exception:
                    continue

            if not body:
                continue
            if _looks_like_group(title):
                logger.info("WA Web skip group chat title=%r", title[:40])
                continue

            phone_hint = _phone_from_page(page) or _phone_from_title(title) or ""
            results.append(
                {
                    "chat_title": title[:255],
                    "body": body[:8000],
                    "phone_hint": phone_hint,
                }
            )
            logger.info(
                "WA Web detected inbound title=%r phone=%s len=%s",
                title[:40],
                (phone_hint[-4:] if phone_hint else "-"),
                len(body),
            )

        return results

    return wa_web_browser.run(_poll, timeout=45.0)