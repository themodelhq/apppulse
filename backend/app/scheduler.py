"""
Background refresh scheduler.

Uses APScheduler (in-process) rather than a separate Celery/RabbitMQ
cluster to keep the first working version simple to run locally. The
provider layer (scrapers/) and the job function below are written so
swapping this for Celery workers later is a small change, not a rewrite -
see the README roadmap section.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import App, Snapshot, Estimate, Alert, AlertType, Store, Milestone
from app.scrapers.orchestrator import fetch_all_sources
from app.estimation import estimate_daily_downloads
from app.websocket_manager import manager

logger = logging.getLogger("apppulse.scheduler")
settings = get_settings()

scheduler = AsyncIOScheduler()


def refresh_one_app_sync(db: Session, app_row: App) -> dict:
    """Fetch latest data for one app (primary + fallback sources) and persist
    a new snapshot + estimate. Never silently substitutes fabricated data:
    if every source fails, the snapshot's rating/rating_count/etc. stay
    null and the estimate comes back as 'insufficient_data'."""
    result = fetch_all_sources(
        store=app_row.store,
        store_id=app_row.store_id,
        country=app_row.country,
        app_name_hint=app_row.name,
    )

    if result.primary_error and not result.sources:
        # Every source failed - record nothing fabricated, just log it.
        logger.error("All sources failed for app %s (%s): %s", app_row.id, app_row.store_id, result.primary_error)
        return {"app_id": app_row.id, "error": result.primary_error}

    try:
        meta = result.metadata
        snapshot = Snapshot(
            app_id=app_row.id,
            rating=result.rating,
            rating_count=result.rating_count,
            install_bucket_min=result.install_bucket_min,
            category_rank=result.appbrain_rank,
            sources=result.sources,
            raw=None,  # dropped to keep row size sane; provider modules still return full raw payloads if you want to log them
            fetched_at=datetime.utcnow(),
        )
        app_row.name = meta.get("name") or app_row.name
        app_row.developer = meta.get("developer") or app_row.developer
        app_row.category = meta.get("category") or app_row.category
        app_row.icon_url = meta.get("icon_url") or app_row.icon_url
        app_row.price = meta.get("price") or app_row.price
        app_row.version = meta.get("version") or app_row.version
        app_row.url = meta.get("url") or app_row.url

        db.add(snapshot)
        app_row.updated_at = datetime.utcnow()
        db.flush()

        if result.milestone:
            db.add(Milestone(
                app_id=app_row.id,
                source=result.milestone["source"],
                source_url=result.milestone["article_url"],
                reported_downloads=result.milestone["milestone_downloads"],
                context=result.milestone["context_sentence"],
            ))

        # Pull the prior snapshot (before the one we just added) to diff against.
        prior = (
            db.execute(
                select(Snapshot)
                .where(Snapshot.app_id == app_row.id, Snapshot.id != snapshot.id)
                .order_by(Snapshot.fetched_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        hours_between = None
        if prior:
            hours_between = (snapshot.fetched_at - prior.fetched_at).total_seconds() / 3600

        est_result = estimate_daily_downloads(
            snapshot, prior, hours_between,
            appbrain_rank=result.appbrain_rank,
            milestone=result.milestone,
        )
        estimate = Estimate(
            app_id=app_row.id,
            estimated_daily_downloads=est_result.estimated_daily_downloads,
            low_bound=est_result.low_bound,
            high_bound=est_result.high_bound,
            confidence_pct=est_result.confidence_pct,
            method=est_result.method,
            notes=est_result.notes,
        )
        db.add(estimate)

        _check_alerts(db, app_row, snapshot, prior)

        db.commit()
        return {
            "app_id": app_row.id,
            "name": app_row.name,
            "estimated_daily_downloads": est_result.estimated_daily_downloads,
            "confidence_pct": est_result.confidence_pct,
            "sources": result.sources,
            "fetched_at": snapshot.fetched_at.isoformat(),
        }
    except Exception as exc:
        logger.exception("Failed to persist refresh for app %s (%s): %s", app_row.id, app_row.store_id, exc)
        db.rollback()
        return {"app_id": app_row.id, "error": str(exc)}


def _check_alerts(db: Session, app_row: App, latest: Snapshot, prior: Snapshot | None) -> None:
    if not prior:
        return
    if prior.rating and latest.rating and latest.rating < prior.rating - 0.15:
        db.add(Alert(
            app_id=app_row.id,
            type=AlertType.RATING_DROP,
            message=f"{app_row.name} rating dropped from {prior.rating:.2f} to {latest.rating:.2f}",
        ))
    if (
        prior.rating_count and latest.rating_count
        and latest.rating_count - prior.rating_count > max(50, prior.rating_count * 0.1)
    ):
        db.add(Alert(
            app_id=app_row.id,
            type=AlertType.NEW_REVIEW_SPIKE,
            message=f"{app_row.name} saw a spike in new reviews since last check",
        ))


def _refresh_by_id_sync(app_id: str) -> dict:
    """Open a fresh session, load the app fresh, and refresh it. Keeps each
    app's DB work self-contained so one failing app can't poison another's
    session/transaction."""
    db = SessionLocal()
    try:
        app_row = db.get(App, app_id)
        if not app_row:
            return {"app_id": app_id, "error": "app no longer exists"}
        return refresh_one_app_sync(db, app_row)
    finally:
        db.close()


async def refresh_all_apps() -> None:
    """Scheduler job: refresh every active, non-archived tracked app."""
    db = SessionLocal()
    try:
        app_ids = db.execute(
            select(App.id).where(App.is_active.is_(True), App.is_archived.is_(False))
        ).scalars().all()
    finally:
        db.close()

    results = []
    for app_id in app_ids:
        results.append(await asyncio.to_thread(_refresh_by_id_sync, app_id))

    if results:
        await manager.broadcast({"type": "refresh", "results": results, "at": datetime.utcnow().isoformat()})


def start_scheduler() -> None:
    scheduler.add_job(
        refresh_all_apps,
        "interval",
        seconds=settings.REFRESH_INTERVAL_SECONDS,
        id="refresh_all_apps",
        replace_existing=True,
        next_run_time=datetime.utcnow(),  # run once immediately on startup
    )
    scheduler.start()
