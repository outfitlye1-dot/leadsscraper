"""Image extraction: srcset, lazy-load, hashing."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass
class ImageAsset:
    url: str
    alt: str = ""
    width: int | None = None
    height: int | None = None
    is_logo: bool = False
    content_hash: str = ""


@dataclass
class ImageExtractionResult:
    images: list[ImageAsset] = field(default_factory=list)
    logo_url: str | None = None

    def dedupe(self) -> ImageExtractionResult:
        seen: set[str] = set()
        unique: list[ImageAsset] = []
        for img in self.images:
            key = img.content_hash or img.url
            if key in seen:
                continue
            seen.add(key)
            unique.append(img)
        self.images = unique
        return self


def _parse_srcset(srcset: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for part in srcset.split(","):
        piece = part.strip().split()[0] if part.strip() else ""
        if piece:
            urls.append(urljoin(base_url, piece))
    return urls


def _hash_url(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def extract_images(html: str, base_url: str, *, max_images: int = 20) -> ImageExtractionResult:
    soup = BeautifulSoup(html, "html.parser")
    result = ImageExtractionResult()
    logo_candidates: list[ImageAsset] = []

    for img in soup.find_all("img"):
        if len(result.images) >= max_images:
            break
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("data-original")
            or ""
        ).strip()
        if not src and img.get("srcset"):
            parts = _parse_srcset(img["srcset"], base_url)
            src = parts[-1] if parts else ""
        if not src or src.startswith("data:"):
            continue
        full = urljoin(base_url, src)
        alt = (img.get("alt") or "").strip()
        is_logo = bool(re.search(r"logo|brand|icon", alt, re.I)) or "logo" in full.lower()
        asset = ImageAsset(
            url=full,
            alt=alt,
            is_logo=is_logo,
            content_hash=_hash_url(full),
        )
        if img.get("srcset"):
            for u in _parse_srcset(img["srcset"], base_url):
                if u != full:
                    result.images.append(
                        ImageAsset(url=u, alt=alt, content_hash=_hash_url(u))
                    )
        result.images.append(asset)
        if is_logo:
            logo_candidates.append(asset)

    # og:image as logo fallback
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        og_url = urljoin(base_url, og["content"])
        result.images.append(ImageAsset(url=og_url, is_logo=True, content_hash=_hash_url(og_url)))
        logo_candidates.append(result.images[-1])

    if logo_candidates:
        result.logo_url = logo_candidates[0].url

    return result.dedupe()
