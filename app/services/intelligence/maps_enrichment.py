"""Google Maps / Apify field enrichment."""

from __future__ import annotations

import json


def enrich_maps_lead(item: dict, mapped: dict) -> dict:
    """Extract reviews, rating, hours, photos, profile completeness from Apify raw item."""
    reviews = (
        item.get("reviewsCount")
        or item.get("totalReviews")
        or item.get("reviews")
        or item.get("userRatingsTotal")
    )
    if isinstance(reviews, list):
        reviews = len(reviews)
    try:
        reviews_count = int(reviews) if reviews is not None else None
    except (TypeError, ValueError):
        reviews_count = None

    rating_raw = (
        item.get("totalScore")
        or item.get("rating")
        or item.get("stars")
        or item.get("averageRating")
    )
    try:
        rating = float(rating_raw) if rating_raw is not None else None
    except (TypeError, ValueError):
        rating = None

    hours = item.get("openingHours") or item.get("opening_hours") or item.get("workHours")
    if isinstance(hours, (dict, list)):
        business_hours = json.dumps(hours)[:2000]
    elif hours:
        business_hours = str(hours)[:2000]
    else:
        business_hours = None

    images = item.get("imageUrls") or item.get("images") or item.get("photos")
    photos_count = len(images) if isinstance(images, list) else None
    if photos_count is None:
        pc = item.get("imagesCount") or item.get("photosCount")
        try:
            photos_count = int(pc) if pc is not None else None
        except (TypeError, ValueError):
            photos_count = None

    profile_score = 0
    if mapped.get("phone"):
        profile_score += 20
    if mapped.get("website") and "google" not in str(mapped.get("website", "")).lower():
        profile_score += 15
    if mapped.get("address"):
        profile_score += 15
    if reviews_count and reviews_count > 0:
        profile_score += 20
    if rating and rating >= 4.0:
        profile_score += 15
    if photos_count and photos_count >= 3:
        profile_score += 15
    if business_hours:
        profile_score += 10

    mapped["reviews_count"] = reviews_count
    mapped["rating"] = rating
    mapped["business_hours"] = business_hours
    mapped["photos_count"] = photos_count
    mapped["google_profile_score"] = min(100, profile_score)

    meta = dict(mapped.get("intelligence_meta") or {})
    if item.get("ownerResponseRate") or item.get("responseRate"):
        meta["owner_response_active"] = True
    if reviews_count and reviews_count >= 10:
        meta["recent_review_activity"] = True
    mapped["intelligence_meta"] = meta
    return mapped
