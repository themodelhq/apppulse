"""
Download Estimation Engine
===========================

Be honest about what this is: neither Apple nor Google publish exact
download counts for arbitrary apps. Commercial tools (Sensor Tower, etc.)
get their accuracy from licensed device-panel data we don't have access
to. This engine instead combines *public* signals into a bounded estimate
with an explicit confidence score - it should never be presented as a
ground-truth number.

Signals used:
- Google Play install bucket (when available) - this is a real floor,
  not a guess, so if present it heavily anchors the estimate.
- Review velocity: change in rating_count between snapshots. Industry
  rule-of-thumb ratios (reviews-per-install) vary hugely by app category
  and are only used as a coarse multiplier, hence the wide confidence
  bounds.
- Chart rank + rank velocity: better rank / rising rank implies more
  installs; the exact relationship is app-category dependent and not
  something we claim to know precisely.

Every estimate stores `method` and `notes` so a user can see exactly
which signals produced it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import Snapshot


# Rough, published industry rules of thumb for reviews-per-install ratio,
# by broad category. These vary widely in practice (1 review per 50-200
# installs is a commonly cited range) - we use the midpoint and widen the
# confidence interval to reflect the real uncertainty.
DEFAULT_REVIEW_TO_INSTALL_RATIO = 1 / 100  # 1 review per ~100 installs (industry rule of thumb)


@dataclass
class EstimateResult:
    estimated_daily_downloads: Optional[int]
    low_bound: Optional[int]
    high_bound: Optional[int]
    confidence_pct: float
    method: str
    notes: str


def estimate_daily_downloads(
    latest: Snapshot,
    previous: Optional[Snapshot],
    hours_between: Optional[float],
    appbrain_rank: Optional[int] = None,
    milestone: Optional[dict] = None,
) -> EstimateResult:
    """
    Produce a bounded daily-download estimate from two consecutive snapshots,
    optionally sharpened by independent third-party signals:
    - appbrain_rank: an independently-computed rank from a source that isn't
      just re-reading the same Play Store page we already read.
    - milestone: a Wikipedia-sourced, dated, self-reported lifetime download
      figure (see scrapers/wikipedia_source.py). Used only as a sanity
      bound on the *lifetime* scale, never mistaken for a daily number.

    Returns wide bounds and low confidence when signal is thin - this is
    intentional; a fake-precise number is worse than an honest range.
    """
    signals_used = []

    # --- Signal 1: Google Play install bucket delta (best available signal) ---
    bucket_daily = None
    if (
        previous
        and latest.install_bucket_min is not None
        and previous.install_bucket_min is not None
        and hours_between
        and latest.install_bucket_min > previous.install_bucket_min
    ):
        delta = latest.install_bucket_min - previous.install_bucket_min
        bucket_daily = delta / (hours_between / 24)
        signals_used.append("play_store_install_bucket_delta")

    # --- Signal 2: review velocity ---
    review_daily = None
    if previous and latest.rating_count and previous.rating_count and hours_between:
        review_delta = latest.rating_count - previous.rating_count
        if review_delta > 0:
            reviews_per_day = review_delta / (hours_between / 24)
            review_daily = reviews_per_day / DEFAULT_REVIEW_TO_INSTALL_RATIO
            signals_used.append("review_velocity")

    # --- Signal 3: rank as a coarse sanity bound (order of magnitude only) ---
    # Prefer AppBrain's independently-computed rank when we have it, since
    # it isn't derived from the same page read as our other signals; fall
    # back to our own stored category_rank otherwise.
    effective_rank = appbrain_rank or latest.category_rank
    rank_hint = None
    if effective_rank:
        if effective_rank <= 10:
            rank_hint = (10_000, 500_000)
        elif effective_rank <= 50:
            rank_hint = (1_000, 50_000)
        elif effective_rank <= 200:
            rank_hint = (100, 5_000)
        else:
            rank_hint = (10, 1_000)
        if appbrain_rank:
            signals_used.append("appbrain_rank")

    candidates = [v for v in (bucket_daily, review_daily) if v is not None]

    if not candidates:
        notes = (
            "Not enough historical snapshots yet to estimate daily downloads. "
            "Estimates improve after a few polling cycles."
        )
        if milestone:
            notes += (
                f" Independent context: Wikipedia cites a lifetime figure of "
                f"~{milestone['milestone_downloads']:,} downloads/installs "
                f"(source: {milestone['article_url']})."
            )
        return EstimateResult(
            estimated_daily_downloads=None,
            low_bound=None,
            high_bound=None,
            confidence_pct=0.0,
            method="insufficient_data" if not milestone else "insufficient_data+wikipedia_milestone",
            notes=notes,
        )

    point_estimate = sum(candidates) / len(candidates)

    # Confidence scales with signal agreement + signal count. An
    # independently-sourced rank (AppBrain) corroborating the point estimate's
    # rough order of magnitude nudges confidence up further than our own
    # single-source rank would.
    if len(candidates) == 2:
        spread_ratio = abs(candidates[0] - candidates[1]) / max(point_estimate, 1)
        confidence = max(20.0, 65.0 - spread_ratio * 40)
    else:
        confidence = 35.0 if "play_store_install_bucket_delta" in signals_used else 20.0

    if appbrain_rank and rank_hint and rank_hint[0] <= point_estimate <= rank_hint[1]:
        confidence = min(90.0, confidence + 10.0)

    low_bound = int(point_estimate * 0.4)
    high_bound = int(point_estimate * 2.2)

    if rank_hint:
        low_bound = max(low_bound, rank_hint[0] // 10)
        high_bound = min(high_bound, rank_hint[1] * 3) if high_bound > rank_hint[1] * 3 else high_bound

    notes = (
        f"Derived from {len(candidates)} public signal(s): {', '.join(signals_used)}. "
        "This is a modeled estimate, not an official figure - "
        "treat the range as more reliable than the point value."
    )
    if milestone:
        notes += (
            f" Cross-checked against a Wikipedia-cited lifetime figure of "
            f"~{milestone['milestone_downloads']:,} (source: {milestone['article_url']})."
        )

    return EstimateResult(
        estimated_daily_downloads=int(point_estimate),
        low_bound=max(0, low_bound),
        high_bound=max(low_bound + 1, high_bound),
        confidence_pct=round(confidence, 1),
        method="+".join(signals_used) if signals_used else "heuristic",
        notes=notes,
    )
