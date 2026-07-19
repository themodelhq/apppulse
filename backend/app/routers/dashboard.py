from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import App, Snapshot, Estimate, Alert
from app.schemas import KpiOut, AlertOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=KpiOut)
def get_kpis(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    thirty_days_ago = now - timedelta(days=30)

    total_apps = db.execute(
        select(func.count()).select_from(App).where(App.is_archived.is_(False))
    ).scalar_one()

    def sum_estimates_between(start, end) -> int:
        # Latest estimate per app within the window, summed.
        subq = (
            select(
                Estimate.app_id,
                func.max(Estimate.created_at).label("max_created")
            )
            .where(Estimate.created_at >= start, Estimate.created_at < end)
            .group_by(Estimate.app_id)
            .subquery()
        )
        rows = db.execute(
            select(Estimate.estimated_daily_downloads)
            .join(subq, (Estimate.app_id == subq.c.app_id) & (Estimate.created_at == subq.c.max_created))
        ).scalars().all()
        return int(sum(v for v in rows if v))

    today_dl = sum_estimates_between(today_start, now)
    yesterday_dl = sum_estimates_between(yesterday_start, today_start)
    thirty_day_dl = sum_estimates_between(thirty_days_ago, now)

    avg_rating = db.execute(
        select(func.avg(Snapshot.rating)).where(Snapshot.fetched_at >= thirty_days_ago)
    ).scalar_one()

    reviews_today = db.execute(
        select(func.count()).select_from(Snapshot).where(Snapshot.fetched_at >= today_start)
    ).scalar_one()

    countries = db.execute(select(func.count(func.distinct(App.country)))).scalar_one()

    alerts_today = db.execute(
        select(func.count()).select_from(Alert).where(Alert.created_at >= today_start)
    ).scalar_one()

    return KpiOut(
        total_apps_tracked=total_apps,
        today_estimated_downloads=today_dl,
        yesterday_estimated_downloads=yesterday_dl,
        thirty_day_estimated_downloads=thirty_day_dl,
        average_rating=round(avg_rating, 2) if avg_rating else None,
        reviews_today=reviews_today,
        countries_monitored=countries,
        alerts_triggered_today=alerts_today,
    )


@router.get("/alerts", response_model=list[AlertOut])
def get_alerts(db: Session = Depends(get_db), limit: int = 50):
    rows = db.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    ).scalars().all()
    return rows
