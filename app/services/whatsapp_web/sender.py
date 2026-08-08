"""Send WhatsApp Web messages via Playwright (human-like delays)."""



from __future__ import annotations



import logging

import random

import re

import time

from typing import Any



from app.services.whatsapp_web.browser import wa_web_browser



logger = logging.getLogger(__name__)



_SEARCH_OPEN_SELECTORS = [

    '[data-testid="chat-list-search"]',

    'button[aria-label="Search or start new chat"]',

    'button[aria-label*="Search" i]',

    '[data-testid="search"]',

    'span[data-icon="search"]',

    'span[data-icon="search-refreshed"]',

    '#side button[aria-label*="Search" i]',

]



_SEARCH_INPUT_SELECTORS = [

    'div[contenteditable="true"][data-tab="3"]',

    '[data-testid="chat-list-search"] div[contenteditable="true"]',

    '#side div[contenteditable="true"][role="textbox"]',

    'div[title="Search input textbox"]',

    'div[aria-label="Search input textbox"]',

    'div[aria-label*="Search" i][contenteditable="true"]',

]



_COMPOSE_SELECTORS = [

    'div[contenteditable="true"][data-tab="10"]',

    'footer div[contenteditable="true"]',

    '#main footer div[contenteditable="true"]',

    '#main div[contenteditable="true"][role="textbox"]',

]



_HEADER_TITLE_SELECTORS = [

    'header span[dir="auto"]',

    'header [data-testid="conversation-info-header-chat-title"]',

    "#main header span[title]",

]





def _type_human(locator: Any, text: str, delay_ms: int = 40) -> None:

    locator.click(timeout=5000)

    time.sleep(random.uniform(0.2, 0.5))

    for ch in text:

        locator.type(ch, delay=max(15, delay_ms + random.randint(-10, 25)))





def _first_visible(page: Any, selectors: list[str], timeout_ms: int = 1500) -> Any | None:

    for sel in selectors:

        try:

            loc = page.locator(sel).first

            if loc.count() == 0:

                continue

            try:

                visible = loc.is_visible(timeout=timeout_ms)

            except TypeError:

                visible = loc.is_visible()

            if visible:

                return loc

        except Exception:

            continue

    return None





def _header_title(page: Any) -> str:

    for sel in _HEADER_TITLE_SELECTORS:

        try:

            loc = page.locator(sel).first

            if loc.count() == 0:

                continue

            title = (loc.get_attribute("title") or loc.inner_text(timeout=1000) or "").strip()

            if title:

                return title

        except Exception:

            continue

    return ""





def _titles_match(a: str, b: str) -> bool:

    left = re.sub(r"\s+", " ", (a or "").strip().lower())

    right = re.sub(r"\s+", " ", (b or "").strip().lower())

    if not left or not right:

        return False

    if left == right:

        return True

    if left in right or right in left:

        return True

    ld = re.sub(r"\D", "", left)

    rd = re.sub(r"\D", "", right)

    return bool(ld and rd and (ld in rd or rd in ld) and min(len(ld), len(rd)) >= 10)





def _open_compose(page: Any) -> Any:

    compose = _first_visible(page, _COMPOSE_SELECTORS, timeout_ms=2500)

    if compose is None:

        raise RuntimeError("WhatsApp compose box not found — chat may not have opened")

    return compose





def _try_open_chat_by_list(page: Any, query: str) -> bool:

    """Click a visible chat row whose title matches query (no search box needed)."""

    q = (query or "").strip()

    if len(q) < 2:

        return False

    row_sels = [

        '#pane-side div[role="listitem"]',

        '#pane-side div[role="row"]',

    ]

    for sel in row_sels:

        try:

            rows = page.locator(sel)

            count = min(rows.count(), 50)

            for i in range(count):

                row = rows.nth(i)

                try:

                    if not row.is_visible(timeout=300):

                        continue

                    text = (row.inner_text(timeout=600) or "").strip()

                except Exception:

                    continue

                first_line = text.split("\n", 1)[0].strip()

                if _titles_match(first_line, q) or _titles_match(text, q):

                    row.click(timeout=4000)

                    time.sleep(0.9)

                    return True

        except Exception:

            continue

    return False





def _focus_search(page: Any) -> Any:

    search = _first_visible(page, _SEARCH_INPUT_SELECTORS, timeout_ms=1200)

    if search is not None:

        return search



    opener = _first_visible(page, _SEARCH_OPEN_SELECTORS, timeout_ms=2000)

    if opener is not None:

        try:

            opener.click(timeout=4000)

            time.sleep(0.5)

        except Exception:

            pass



    search = _first_visible(page, _SEARCH_INPUT_SELECTORS, timeout_ms=2500)

    if search is not None:

        return search



    # Keyboard shortcut used by WhatsApp Web / Desktop-like layouts

    try:

        page.keyboard.press("Control+Alt+/")

        time.sleep(0.4)

    except Exception:

        pass

    search = _first_visible(page, _SEARCH_INPUT_SELECTORS, timeout_ms=2000)

    if search is not None:

        return search



    raise RuntimeError("WhatsApp search box not found")





def send_text(

    *,

    search_query: str,

    body: str,

    typing_delay_ms: int = 40,

) -> None:

    """Open chat (reuse open tab / list / search), type message, press Enter."""

    query = (search_query or "").strip()

    text = (body or "").strip()

    if not query or not text:

        raise ValueError("search_query and body required")



    def _send(page: Any) -> None:

        from app.services.whatsapp_web.session import _is_logged_in_on_page



        if not _is_logged_in_on_page(page):

            raise RuntimeError("WhatsApp Web not logged in")



        opened = False

        current = _header_title(page)

        if _titles_match(current, query):

            opened = True

            logger.info("WA Web send: already on chat %r", current[:40])

        elif _try_open_chat_by_list(page, query):

            opened = True

            logger.info("WA Web send: opened chat from list for %r", query[:40])

        else:

            search = _focus_search(page)

            search.click(timeout=4000)

            time.sleep(0.25)

            try:

                page.keyboard.press("Control+A")

                page.keyboard.press("Backspace")

            except Exception:

                pass

            _type_human(search, query, delay_ms=typing_delay_ms)

            time.sleep(1.4)

            page.keyboard.press("Enter")

            time.sleep(1.1)

            opened = True

            logger.info("WA Web send: opened chat via search for %r", query[:40])



        if not opened:

            raise RuntimeError(f"Could not open chat for {query!r}")



        compose = _open_compose(page)

        time.sleep(random.uniform(0.5, 1.2))

        _type_human(compose, text[:4000], delay_ms=typing_delay_ms)

        time.sleep(random.uniform(0.3, 0.7))

        page.keyboard.press("Enter")

        logger.info("WA Web sent reply to query=%r chars=%s", query[:40], len(text))



    wa_web_browser.run(_send, timeout=120.0)





def normalize_search_target(phone_hint: str | None, chat_title: str) -> str:

    digits = re.sub(r"\D", "", phone_hint or "")

    if len(digits) >= 10:

        return digits

    return (chat_title or "").strip()


