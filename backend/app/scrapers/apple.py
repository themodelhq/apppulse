"""
Apple App Store data source.

Unlike Google Play, Apple actually publishes two genuinely free, public,
official JSON endpoints we can lean on instead of scraping HTML:

1. iTunes Lookup API - per-app metadata, ratings, price, version, etc.
   https://itunes.apple.com/lookup?id=<numeric_id>&country=<cc>

2. Apple RSS "Marketing Tools" feed - top charts per country/category.
   https://rss.applemarketingtools.com/api/v2/<cc>/apps/top-free/200/apps.json

Neither exposes install counts (Apple has never published those), so
"downloads" for Apple apps are always modeled - see estimation.py.
"""
from __future__ import annotations

import httpx
from datetime import datetime
from typing import Optional

from app.config import get_settings

settings = get_settings()

HEADERS = {"User-Agent": settings.SCRAPER_USER_AGENT}


class AppleScrapeError(Exception):
    pass


def _client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=settings.SCRAPER_TIMEOUT_SECONDS)


def fetch_app_metadata(app_id: str, country: str = "us") -> dict:
    """Fetch metadata for a single app via the official iTunes Lookup API."""
    url = "https://itunes.apple.com/lookup"
    params = {"id": app_id, "country": country}

    last_exc: Optional[Exception] = None
    for attempt in range(settings.SCRAPER_MAX_RETRIES):
        try:
            with _client() as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if not data.get("results"):
                    raise AppleScrapeError(
                        f"No app found for id={app_id} country={country}"
                    )
                r = data["results"][0]
                return {
                    "name": r.get("trackName"),
                    "developer": r.get("artistName"),
                    "category": r.get("primaryGenreName"),
                    "icon_url": r.get("artworkUrl512") or r.get("artworkUrl100"),
                    "description": r.get("description"),
                    "price": "Free" if r.get("price") == 0 else f"${r.get('price')}",
                    "version": r.get("version"),
                    "release_date": r.get("releaseDate"),
                    "updated_date": r.get("currentVersionReleaseDate"),
                    "content_rating": r.get("trackContentRating"),
                    "url": r.get("trackViewUrl"),
                    "rating": r.get("averageUserRating"),
                    "rating_count": r.get("userRatingCount"),
                    "rating_count_current_version": r.get("userRatingCountForCurrentVersion"),
                    "supported_devices": r.get("supportedDevices", []),
                    "languages": r.get("languageCodesISO2A", []),
                    "raw": r,
                }
        except (httpx.HTTPError, AppleScrapeError) as exc:
            last_exc = exc
            continue
    raise AppleScrapeError(f"Failed to fetch app {app_id} after retries: {last_exc}")


def fetch_top_chart(country: str = "us", chart: str = "top-free", limit: int = 200) -> list[dict]:
    """
    Pull Apple's official top charts feed. `chart` is one of:
    top-free, top-paid, top-grossing.
    Returns a list of {store_id, name, developer, category, rank}.
    """
    url = f"https://rss.applemarketingtools.com/api/v2/{country}/apps/{chart}/{limit}/apps.json"
    with _client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()

    entries = data.get("feed", {}).get("results", [])
    out = []
    for idx, e in enumerate(entries, start=1):
        out.append({
            "store_id": e.get("id"),
            "name": e.get("name"),
            "developer": e.get("artistName"),
            "category": (e.get("genres") or [{}])[0].get("name"),
            "rank": idx,
            "chart_type": chart.replace("-", "_"),
        })
    return out


def parse_release_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
