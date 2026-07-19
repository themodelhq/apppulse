from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import App, Snapshot, Estimate, Store, Milestone
from app.schemas import AppCreate, AppOut, AppDetailOut, SnapshotOut, EstimateOut, MilestoneOut
from app.scheduler import _refresh_by_id_sync

router = APIRouter(prefix="/api/apps", tags=["apps"])


@router.get("", response_model=list[AppOut])
def list_apps(
    db: Session = Depends(get_db),
    archived: bool = False,
    favorite: bool | None = None,
    store: str | None = None,
    q: str | None = None,
):
    stmt = select(App).where(App.is_archived.is_(archived))
    if favorite is not None:
        stmt = stmt.where(App.is_favorite.is_(favorite))
    if store:
        stmt = stmt.where(App.store == store)
    if q:
        stmt = stmt.where(App.name.ilike(f"%{q}%"))
    return db.execute(stmt.order_by(App.created_at.desc())).scalars().all()


@router.post("", response_model=AppOut, status_code=201)
def add_app(payload: AppCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if payload.store not in (Store.APPLE.value, Store.GOOGLE.value):
        raise HTTPException(400, "store must be 'apple_app_store' or 'google_play'")

    existing = db.execute(
        select(App).where(
            App.store == payload.store,
            App.store_id == payload.store_id,
            App.country == payload.country,
        )
    ).scalars().first()
    if existing:
        raise HTTPException(409, "This app is already tracked")

    app_row = App(store=payload.store, store_id=payload.store_id, country=payload.country)
    db.add(app_row)
    db.commit()
    db.refresh(app_row)

    # Kick off an immediate first fetch in the background so the user doesn't
    # stare at a blank profile until the next scheduled cycle.
    background_tasks.add_task(_refresh_by_id_sync, app_row.id)

    return app_row


@router.get("/{app_id}", response_model=AppDetailOut)
def get_app(app_id: str, days: int = 30, db: Session = Depends(get_db)):
    app_row = db.get(App, app_id)
    if not app_row:
        raise HTTPException(404, "App not found")

    since = datetime.utcnow() - timedelta(days=days)
    history = db.execute(
        select(Snapshot)
        .where(Snapshot.app_id == app_id, Snapshot.fetched_at >= since)
        .order_by(Snapshot.fetched_at.asc())
    ).scalars().all()

    latest_snapshot = history[-1] if history else None
    latest_estimate = db.execute(
        select(Estimate).where(Estimate.app_id == app_id).order_by(Estimate.created_at.desc()).limit(1)
    ).scalars().first()
    milestones = db.execute(
        select(Milestone).where(Milestone.app_id == app_id).order_by(Milestone.found_at.desc())
    ).scalars().all()

    out = AppDetailOut.model_validate(app_row)
    out.history = [SnapshotOut.model_validate(s) for s in history]
    out.latest_snapshot = SnapshotOut.model_validate(latest_snapshot) if latest_snapshot else None
    out.latest_estimate = EstimateOut.model_validate(latest_estimate) if latest_estimate else None
    out.milestones = [MilestoneOut.model_validate(m) for m in milestones]
    return out


@router.patch("/{app_id}", response_model=AppOut)
def update_app(app_id: str, is_favorite: bool | None = None, is_archived: bool | None = None,
               tags: list[str] | None = None, db: Session = Depends(get_db)):
    app_row = db.get(App, app_id)
    if not app_row:
        raise HTTPException(404, "App not found")
    if is_favorite is not None:
        app_row.is_favorite = is_favorite
    if is_archived is not None:
        app_row.is_archived = is_archived
    if tags is not None:
        app_row.tags = tags
    db.commit()
    db.refresh(app_row)
    return app_row


@router.delete("/{app_id}", status_code=204)
def delete_app(app_id: str, db: Session = Depends(get_db)):
    app_row = db.get(App, app_id)
    if not app_row:
        raise HTTPException(404, "App not found")
    db.delete(app_row)
    db.commit()


@router.post("/{app_id}/refresh", response_model=AppDetailOut)
def force_refresh(app_id: str, db: Session = Depends(get_db)):
    app_row = db.get(App, app_id)
    if not app_row:
        raise HTTPException(404, "App not found")
    _refresh_by_id_sync(app_id)
    return get_app(app_id, days=30, db=db)
