"""
Core data model.

Design notes:
- `App` is the canonical tracked entity (one row per app, per store).
- `Snapshot` is an append-only time series row written every time the
  scheduler polls a source. This is what powers historical charts,
  growth %, and the estimation engine (which looks at deltas across
  snapshots rather than trusting any single reading).
- `Estimate` stores the *derived* daily download estimate + confidence,
  kept separate from raw `Snapshot` data so raw provider data and our
  own modeling assumptions never get conflated.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Enum, Boolean, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Store(str, enum.Enum):
    APPLE = "apple_app_store"
    GOOGLE = "google_play"


class App(Base):
    __tablename__ = "apps"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    store = Column(Enum(Store), nullable=False)
    store_id = Column(String, nullable=False)      # numeric Apple ID or Play package name
    country = Column(String, default="us")          # storefront country code

    name = Column(String, nullable=True)
    developer = Column(String, nullable=True)
    category = Column(String, nullable=True)
    icon_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    price = Column(String, nullable=True)
    version = Column(String, nullable=True)
    release_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    content_rating = Column(String, nullable=True)
    url = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    is_favorite = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    tags = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    snapshots = relationship("Snapshot", back_populates="app", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="app", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="app", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="app", cascade="all, delete-orphan")


class Snapshot(Base):
    """One raw reading of an app's public metrics at a point in time."""
    __tablename__ = "snapshots"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    app_id = Column(UUID(as_uuid=False), ForeignKey("apps.id"), nullable=False, index=True)

    rating = Column(Float, nullable=True)
    rating_count = Column(Integer, nullable=True)     # total ratings at time of read
    review_count = Column(Integer, nullable=True)
    install_bucket_min = Column(Integer, nullable=True)   # Google Play "1,000,000+" -> 1000000
    install_bucket_max = Column(Integer, nullable=True)   # Google Play range upper bound if known
    category_rank = Column(Integer, nullable=True)
    overall_rank = Column(Integer, nullable=True)
    chart_type = Column(String, nullable=True)  # top_free / top_paid / top_grossing / trending

    # Which provider(s) produced this row's fields, e.g.
    # ["google_play_scraper_lib", "appbrain"]. Lets the UI show real
    # provenance instead of implying every field came from one place.
    sources = Column(JSON, default=list)

    raw = Column(JSON, nullable=True)  # full raw payload for debugging / re-processing

    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)

    app = relationship("App", back_populates="snapshots")


class Milestone(Base):
    """
    A dated, self-reported or third-party-reported download/install figure
    found outside Apple/Google (e.g. a Wikipedia-cited press milestone).
    Kept separate from Snapshot because these are sparse, point-in-time
    facts, not a regular polling series - and because they carry their own
    citation (source_url) so a person can go verify them directly.
    """
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    app_id = Column(UUID(as_uuid=False), ForeignKey("apps.id"), nullable=False, index=True)

    source = Column(String, nullable=False)          # e.g. "wikipedia"
    source_url = Column(String, nullable=True)
    reported_downloads = Column(Integer, nullable=True)
    context = Column(Text, nullable=True)             # the sentence/snippet the figure came from

    found_at = Column(DateTime, default=datetime.utcnow, index=True)

    app = relationship("App", back_populates="milestones")


class Estimate(Base):
    """Derived, model-produced estimate - always separate from raw provider data."""
    __tablename__ = "estimates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    app_id = Column(UUID(as_uuid=False), ForeignKey("apps.id"), nullable=False, index=True)

    estimated_daily_downloads = Column(Integer, nullable=True)
    low_bound = Column(Integer, nullable=True)
    high_bound = Column(Integer, nullable=True)
    confidence_pct = Column(Float, nullable=True)   # 0-100
    method = Column(String, nullable=True)          # which model/heuristic produced this
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    app = relationship("App", back_populates="estimates")


class AlertType(str, enum.Enum):
    RANK_CHANGE = "rank_change"
    RATING_DROP = "rating_drop"
    NEW_REVIEW_SPIKE = "new_review_spike"
    ESTIMATE_SPIKE = "estimate_spike"
    ESTIMATE_DROP = "estimate_drop"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    app_id = Column(UUID(as_uuid=False), ForeignKey("apps.id"), nullable=False, index=True)
    type = Column(Enum(AlertType), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    app = relationship("App", back_populates="alerts")
