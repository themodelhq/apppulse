from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

_LOCAL_DEV_DB_HOST = "postgres"  # the docker-compose service name - only resolvable inside that network


def _resolved_database_url() -> str:
    """
    Fail fast with a clear, actionable message instead of letting SQLAlchemy
    attempt a connection and surface a low-level psycopg DNS traceback
    ("Name or service not known") that gives no hint about the actual cause.

    The single most common way to hit that error on Render: DATABASE_URL
    was never actually set on the service, so it silently fell back to this
    app's local-dev default, which points at a Docker Compose-only hostname
    that doesn't exist anywhere on Render's network.
    """
    url = settings.normalized_database_url()
    if f"@{_LOCAL_DEV_DB_HOST}:" in url and settings.ENV != "development":
        raise RuntimeError(
            "DATABASE_URL is still set to this app's local Docker Compose default "
            f"(host='{_LOCAL_DEV_DB_HOST}'), which only resolves inside a docker-compose "
            "network - not on Render or any other host. This almost always means the "
            "DATABASE_URL environment variable was never actually set on this service.\n\n"
            "Fix: in the Render dashboard, go to your Postgres database -> copy the "
            "'Internal Database URL' -> paste it as DATABASE_URL on your web service's "
            "Environment tab. If you deployed via render.yaml (Blueprint), check that the "
            "database resource name there still matches the `fromDatabase: name:` reference "
            "on the web service - Render auto-suffixes names on conflicts, which breaks that "
            "link silently.\n\n"
            "Set ENV=development to skip this check (e.g. for a deliberately offline test)."
        )
    return url


engine = create_engine(_resolved_database_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
