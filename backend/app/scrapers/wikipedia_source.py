"""
Wikipedia data source.

Uses Wikipedia's official, free, keyless REST/Action API
(https://www.mediawiki.org/wiki/API:Main_page) - not scraping. Many
well-known apps have a Wikipedia article that states a company-reported
download or install milestone, e.g. "As of 2024, the app had been
downloaded over 500 million times" or "installed on over 1 billion
devices". These are genuinely useful anchor points: they're self-reported
by the company (often via press release), dated, and completely
independent of anything Apple or Google expose.

Limitations, stated plainly:
- Coverage is sparse - only apps notable enough to have a Wikipedia page,
  and only if that page happens to cite a download figure.
- Figures are point-in-time and often stale by the time you read them;
  we surface the figure's context sentence so a person can judge staleness
  themselves rather than us guessing at how current it is.
- This is a *milestone*, not a daily download estimate - the estimation
  engine uses it only as a sanity-check anchor, never as the number itself.
"""
from __future__ import annotations

import re
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()
HEADERS = {"User-Agent": f"{settings.SCRAPER_USER_AGENT} (AppPulse Analytics; contact: set-your-contact-email)"}

API_URL = "https://en.wikipedia.org/w/api.php"

_MILESTONE_RE = re.compile(
    r"([\d,.]+)\s*(million|billion)\+?\s+(?:downloads|installs|users)",
    re.IGNORECASE,
)


class WikipediaNotFound(Exception):
    pass


def _client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=settings.SCRAPER_TIMEOUT_SECONDS)


def _find_article_title(query: str) -> Optional[str]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{query} app",
        "format": "json",
        "srlimit": 1,
    }
    with _client() as client:
        resp = client.get(API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    results = data.get("query", {}).get("search", [])
    return results[0]["title"] if results else None


def fetch_download_milestone(app_name: str) -> dict:
    """
    Look up the app's Wikipedia article (if any) and text-mine it for a
    stated download/install milestone. Raises WikipediaNotFound if no
    article or no milestone sentence could be located.
    """
    title = _find_article_title(app_name)
    if not title:
        raise WikipediaNotFound(f"No Wikipedia article found for '{app_name}'")

    params = {
        "action": "query",
        "prop": "extracts",
        "titles": title,
        "format": "json",
        "explaintext": 1,
    }
    with _client() as client:
        resp = client.get(API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    pages = data.get("query", {}).get("pages", {})
    extract = next(iter(pages.values()), {}).get("extract", "") if pages else ""
    if not extract:
        raise WikipediaNotFound(f"No article text for '{title}'")

    for sentence in re.split(r"(?<=[.!?])\s+", extract):
        match = _MILESTONE_RE.search(sentence)
        if match:
            value, unit = match.group(1), match.group(2).lower()
            multiplier = 1_000_000 if unit == "million" else 1_000_000_000
            try:
                count = float(value.replace(",", "")) * multiplier
            except ValueError:
                continue
            return {
                "source": "wikipedia",
                "article_title": title,
                "article_url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "milestone_downloads": int(count),
                "context_sentence": sentence.strip(),
            }

    raise WikipediaNotFound(f"Article '{title}' found but no download milestone sentence")
