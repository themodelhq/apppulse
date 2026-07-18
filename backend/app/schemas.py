from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


class AppCreate(BaseModel):
    store: str            # "apple_app_store" | "google_play"
    store_id: str          # numeric Apple ID, or Play package name (e.g. com.spotify.music)
    country: str = "us"


class AppOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    store: str
    store_id: str
    country: str
    name: Optional[str] = None
    developer: Optional[str] = None
    category: Optional[str] = None
    icon_url: Optional[str] = None
    price: Optional[str] = None
    version: Optional[str] = None
    is_favorite: bool = False
    is_archived: bool = False
    tags: List[str] = []
    updated_at: Optional[datetime] = None


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rating: Optional[float] = None
    rating_count: Optional[int] = None
    review_count: Optional[int] = None
    install_bucket_min: Optional[int] = None
    install_bucket_max: Optional[int] = None
    category_rank: Optional[int] = None
    overall_rank: Optional[int] = None
    chart_type: Optional[str] = None
    sources: List[str] = []
    fetched_at: datetime


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    source_url: Optional[str] = None
    reported_downloads: Optional[int] = None
    context: Optional[str] = None
    found_at: datetime


class EstimateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estimated_daily_downloads: Optional[int] = None
    low_bound: Optional[int] = None
    high_bound: Optional[int] = None
    confidence_pct: Optional[float] = None
    method: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class AppDetailOut(AppOut):
    latest_snapshot: Optional[SnapshotOut] = None
    latest_estimate: Optional[EstimateOut] = None
    history: List[SnapshotOut] = []
    milestones: List[MilestoneOut] = []


class KpiOut(BaseModel):
    total_apps_tracked: int
    today_estimated_downloads: int
    yesterday_estimated_downloads: int
    thirty_day_estimated_downloads: int
    average_rating: Optional[float]
    reviews_today: int
    countries_monitored: int
    alerts_triggered_today: int


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    app_id: str
    type: str
    message: str
    is_read: bool
    created_at: datetime
