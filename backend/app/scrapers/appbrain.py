"""
AppBrain data source.

AppBrain (appbrain.com) is a genuine, independent third party that crawls
Google Play (and publishes App Store chart pages too) and computes its own
rankings and estimates - not affiliated with Apple or Google. Their basic
per-app page is free to view; deeper historical/competitor data requires a
paid "Intelligence" subscription, which this integration does not use.

Why this matters for the estimation engine: AppBrain's rank is an
*independently computed* signal, not derived from the same raw reading we
already have from the Play Store page. Two independent sources agreeing
raises real confidence; this is a genuine second opinion, not a mirror of
the same number.

This provider is best-effort by design: we don't know AppBrain's exact
page-slug convention for every app in advance, so we first search their
site for the package name and follow the top result. If that fails, the
provider returns None and the orchestrator simply proceeds without it -
callers must treat AppBrain as an enrichment source, never a required one.
"""
from __future__ import annotations

import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings

settings = get_settings()
HEADERS = {"User-Agent": settings.SCRAPER_USER_AGENT}


class AppBrainNotFound(Exception):
    pass


def _client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=settings.SCRAPER_TIMEOUT_SECONDS, follow_redirects=True)


def find_app_url(package_name: str) -> Optional[str]:
    """Search AppBrain for a package name and return the first matching app page URL."""
    with _client() as client:
        resp = client.get("https://www.appbrain.com/search", params={"q": package_name})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.select("a[href^='/app/']"):
        href = a.get("href", "")
        if package_name in href:
            return f"https://www.appbrain.com{href}"
    # Fall back to the first app result even if the package id isn't in the
    # URL slug (AppBrain sometimes uses a name-only slug).
    first = soup.select_one("a[href^='/app/']")
    return f"https://www.appbrain.com{first['href']}" if first else None


def fetch_app_stats(package_name: str) -> dict:
    """
    Best-effort fetch of AppBrain's free, publicly visible stats for an app:
    their own rating figure and, where shown without a subscription, an
    overall or category rank. Raises AppBrainNotFound if no matching page
    could be located - callers should treat this as "no data", not an error
    worth surfacing to the user.
    """
    url = find_app_url(package_name)
    if not url:
        raise AppBrainNotFound(f"No AppBrain listing found for {package_name}")

    with _client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    rank = None
    rank_match = re.search(r"Ranked\s+#?([\d,]+)\s+in", html)
    if rank_match:
        rank = int(rank_match.group(1).replace(",", ""))

    rating = None
    rating_tag = soup.select_one("[itemprop='ratingValue']")
    if rating_tag and rating_tag.get("content"):
        try:
            rating = float(rating_tag["content"])
        except ValueError:
            pass

    return {
        "source": "appbrain",
        "url": url,
        "rank": rank,
        "rating": rating,
    }
