"""Automatic scraping strategy selection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from app.scrapers.js_detect import looks_like_js_shell


class FetchStrategy(str, Enum):
    http = "http"
    playwright = "playwright"
    api_intercept = "api_intercept"


@dataclass
class StrategyDecision:
    strategy: FetchStrategy
    reason: str
    framework: str | None = None
    needs_scroll: bool = False
    needs_network_intercept: bool = False


_FRAMEWORK_MARKERS: dict[str, tuple[str, ...]] = {
    "nextjs": ("__next", "_next/static", "next/script"),
    "nuxt": ("__nuxt", "_nuxt/"),
    "react": ("react-root", "data-reactroot", "__react"),
    "vue": ("data-v-", "vue-app", "__vue"),
    "angular": ("ng-version", "ng-app", "angular"),
}


def detect_framework(html: str) -> str | None:
    if not html:
        return None
    low = html[:80_000].lower()
    for name, markers in _FRAMEWORK_MARKERS.items():
        if any(m.lower() in low for m in markers):
            return name
    return None


def has_graphql_hints(html: str) -> bool:
    if not html:
        return False
    low = html[:40_000].lower()
    return "graphql" in low or "/api/graphql" in low or "__graphql" in low


def has_infinite_scroll_hints(html: str) -> bool:
    if not html:
        return False
    low = html[:60_000].lower()
    patterns = (
        "infinite-scroll",
        "load-more",
        "load more",
        "data-infinite",
        "intersectionobserver",
    )
    return any(p in low for p in patterns)


def has_shadow_dom_hints(html: str) -> bool:
    if not html:
        return False
    return "shadowroot" in html.lower() or "attachshadow" in html.lower()


def decide_strategy(
    url: str,
    html: str | None = None,
    *,
    status_code: int | None = None,
    force_playwright: bool = False,
) -> StrategyDecision:
    if force_playwright:
        return StrategyDecision(
            strategy=FetchStrategy.playwright,
            reason="forced browser render",
            needs_scroll=True,
        )

    framework = detect_framework(html) if html else None

    if html and has_graphql_hints(html):
        return StrategyDecision(
            strategy=FetchStrategy.api_intercept,
            reason="GraphQL API detected",
            framework=framework,
            needs_network_intercept=True,
        )

    if html and (looks_like_js_shell(html) or framework in ("nextjs", "nuxt", "react", "vue", "angular")):
        return StrategyDecision(
            strategy=FetchStrategy.playwright,
            reason=f"JS framework ({framework or 'SPA'}) requires browser",
            framework=framework,
            needs_scroll=has_infinite_scroll_hints(html),
            needs_network_intercept=has_graphql_hints(html),
        )

    if html and has_infinite_scroll_hints(html):
        return StrategyDecision(
            strategy=FetchStrategy.playwright,
            reason="infinite scroll / load-more detected",
            framework=framework,
            needs_scroll=True,
        )

    if html and has_shadow_dom_hints(html):
        return StrategyDecision(
            strategy=FetchStrategy.playwright,
            reason="Shadow DOM content",
            framework=framework,
        )

    host = urlparse(url).netloc.lower()
    if host.endswith((".web.app", ".vercel.app", ".netlify.app")):
        return StrategyDecision(
            strategy=FetchStrategy.playwright,
            reason="hosted SPA platform",
            framework=framework or "spa",
            needs_scroll=True,
        )

    if status_code and status_code >= 400:
        return StrategyDecision(
            strategy=FetchStrategy.playwright,
            reason=f"HTTP {status_code} — retry with browser",
        )

    return StrategyDecision(strategy=FetchStrategy.http, reason="static HTML sufficient", framework=framework)
