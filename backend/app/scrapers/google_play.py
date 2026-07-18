"""
Google Play data source.

Primary method: the community-maintained `google-play-scraper` PyPI package
(https://pypi.org/project/google-play-scraper/). It calls the same internal
endpoints the Play Store web app itself uses and is actively maintained
against Google's markup changes, which makes it meaningfully more reliable
than a hand-rolled regex scraper.

Fallback method: if the library raises (network error, app removed, or the
library itself falls behind a Google markup change), we fall back to
scraping the public listing page's JSON-LD block directly. This has fewer
fields but is a second, independent code path - so a single point of
failure doesn't take down Play Store ingestion entirely.

Google publishes no official API for this data. Both methods here are
legitimate public-page reads, not any kind of private/authenticated access.
Respect Google's servers: keep polling intervals conservative
(see config.REFRESH_INTERVAL_SECONDS) and don't parallelize aggressively.
"""
from __future__ import annotations

import json
import re
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()
HEADERS = {
    "User-Agent": settings.SCRAPER_USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
}

_INSTALL_RE = re.compile(r"([\d,\.]+)\s*([KMB]?)\+?\s*(?:downloads|installs)?", re.IGNORECASE)


class GooglePlayScrapeError(Exception):
    pass


def _parse_install_count(text: str) -> Optional[int]:
    if not text:
        return None
    match = _INSTALL_RE.search(text.replace(",", ""))
    if not match:
        return None
    num, suffix = match.group(1), match.group(2).upper()
    try:
        value = float(num)
    except ValueError:
        return None
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000, "": 1}[suffix]
    return int(value * multiplier)


def fetch_app_metadata(package_name: str, country: str = "us", lang: str = "en") -> dict:
    """
    Fetch Play Store metadata for one app. Tries the maintained library
    first; falls back to a direct HTML read of the JSON-LD block if that
    fails for any reason. Raises GooglePlayScrapeError only if BOTH fail.
    """
    try:
        return _fetch_via_library(package_name, country, lang)
    except Exception as lib_exc:
        try:
            return _fetch_via_raw_html(package_name, country, lang)
        except Exception as html_exc:
            raise GooglePlayScrapeError(
                f"Both google-play-scraper and raw HTML fallback failed for "
                f"{package_name}: library_error={lib_exc!r} html_error={html_exc!r}"
            )


def _fetch_via_library(package_name: str, country: str, lang: str) -> dict:
    from google_play_scraper import app as gps_app  # imported lazily so its absence doesn't break module import

    result = gps_app(package_name, lang=lang, country=country)
    installs_text = result.get("installs")  # e.g. "10,000,000+"

    return {
        "name": result.get("title"),
        "developer": result.get("developer"),
        "category": result.get("genre"),
        "icon_url": result.get("icon"),
        "description": result.get("description"),
        "price": "Free" if result.get("free") else result.get("priceText"),
        "version": result.get("version"),
        "content_rating": result.get("contentRating"),
        "rating": result.get("score"),
        "rating_count": result.get("ratings"),
        "review_count": result.get("reviews"),
        "install_bucket_min": _parse_install_count(installs_text) if installs_text else None,
        "installs_text": installs_text,
        "url": result.get("url") or f"https://play.google.com/store/apps/details?id={package_name}",
        "source": "google_play_scraper_lib",
        "raw": {k: v for k, v in result.items() if k not in ("descriptionHTML", "recentChangesHTML")},
    }


def _fetch_via_raw_html(package_name: str, country: str, lang: str) -> dict:
    url = "https://play.google.com/store/apps/details"
    params = {"id": package_name, "hl": lang, "gl": country}

    with httpx.Client(headers=HEADERS, timeout=settings.SCRAPER_TIMEOUT_SECONDS, follow_redirects=True) as client:
        resp = client.get(url, params=params)
        if resp.status_code == 404:
            raise GooglePlayScrapeError(f"App not found: {package_name}")
        resp.raise_for_status()
        html = resp.text

    ld_json = _extract_json_ld(html)
    name = ld_json.get("name")
    developer = (ld_json.get("author") or {}).get("name") if isinstance(ld_json.get("author"), dict) else None
    icon_url = ld_json.get("image")
    rating = rating_count = None
    agg = ld_json.get("aggregateRating")
    if isinstance(agg, dict):
        rating = _safe_float(agg.get("ratingValue"))
        rating_count = _safe_int(agg.get("ratingCount"))

    installs_text = _search_between(html, 'Downloads</div><div class="ClM7O"><span>', "<")

    return {
        "name": name,
        "developer": developer,
        "category": None,
        "icon_url": icon_url,
        "rating": rating,
        "rating_count": rating_count,
        "install_bucket_min": _parse_install_count(installs_text) if installs_text else None,
        "installs_text": installs_text,
        "url": f"https://play.google.com/store/apps/details?id={package_name}",
        "source": "raw_html_fallback",
        "raw": {"json_ld": ld_json},
    }


def _extract_json_ld(html: str) -> dict:
    for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            if data.get("@type") in ("SoftwareApplication", "MobileApplication"):
                return data
        except json.JSONDecodeError:
            continue
    return {}


def _search_between(html: str, start: str, end: str) -> Optional[str]:
    i = html.find(start)
    if i == -1:
        return None
    i += len(start)
    j = html.find(end, i)
    if j == -1:
        return None
    return html[i:j].strip()


def _safe_float(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> Optional[int]:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None
