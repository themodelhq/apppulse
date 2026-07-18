"""
Data source orchestrator.

This is the single place that decides, for a given tracked app, which
providers to call and how to combine what they return. The goal is
resilience: if the primary store source fails (network error, app pulled,
markup change, rate limit), the app still gets *some* real data from an
independent free source instead of going empty.

Order of operations per app:

1. PRIMARY: the app's own store (Apple iTunes Lookup API, or Google Play
   via the google-play-scraper library + raw-HTML fallback).
2. ENRICHMENT (always attempted, best-effort, non-blocking): AppBrain for
   an independent rank/rating reading; Wikipedia for a self-reported
   download milestone. Both failures are silent at the orchestrator level -
   "no data available" is a normal, expected outcome for most apps, not an
   error.

Every field in the returned dict is tagged with which provider produced
it via the `sources` list, so nothing pretends to be more authoritative
than it is.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.models import Store
from app.scrapers import apple, google_play, appbrain, wikipedia_source

logger = logging.getLogger("apppulse.orchestrator")


@dataclass
class FetchResult:
    metadata: dict                      # merged app metadata (name, developer, category, etc.)
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    install_bucket_min: Optional[int] = None
    appbrain_rank: Optional[int] = None
    milestone: Optional[dict] = None    # Wikipedia-sourced milestone, if any
    sources: list[str] = field(default_factory=list)
    primary_error: Optional[str] = None


def fetch_all_sources(store: Store, store_id: str, country: str, app_name_hint: Optional[str] = None) -> FetchResult:
    """
    Fetch everything available for one app across primary + fallback
    sources. Never raises - a total failure comes back as a FetchResult
    with empty fields and `primary_error` set, so the scheduler can still
    log/alert on it without crashing the whole refresh cycle.
    """
    result = FetchResult(metadata={})

    # --- Primary: the app's own store ---
    try:
        if store == Store.APPLE:
            meta = apple.fetch_app_metadata(store_id, country=country)
            result.sources.append("apple_itunes_api")
        else:
            meta = google_play.fetch_app_metadata(store_id, country=country)
            result.sources.append(meta.get("source", "google_play"))

        result.metadata = meta
        result.rating = meta.get("rating")
        result.rating_count = meta.get("rating_count")
        result.install_bucket_min = meta.get("install_bucket_min")
    except Exception as exc:
        logger.warning("Primary source failed for %s/%s: %s", store, store_id, exc)
        result.primary_error = str(exc)

    # Use whatever name we have (from a successful primary fetch, or a
    # caller-supplied hint) to drive the enrichment lookups below.
    name_for_lookup = result.metadata.get("name") or app_name_hint

    # --- Enrichment: AppBrain (independent rank/rating, Android-oriented) ---
    try:
        ab = appbrain.fetch_app_stats(store_id)
        result.appbrain_rank = ab.get("rank")
        result.sources.append("appbrain")
        # If we have no primary rating at all, AppBrain's is better than nothing.
        if result.rating is None and ab.get("rating") is not None:
            result.rating = ab["rating"]
    except Exception as exc:
        logger.info("AppBrain enrichment unavailable for %s: %s", store_id, exc)

    # --- Enrichment: Wikipedia (self-reported milestone, sparse but independent) ---
    if name_for_lookup:
        try:
            milestone = wikipedia_source.fetch_download_milestone(name_for_lookup)
            result.milestone = milestone
            result.sources.append("wikipedia")
        except Exception as exc:
            logger.info("Wikipedia enrichment unavailable for %s: %s", name_for_lookup, exc)

    return result
