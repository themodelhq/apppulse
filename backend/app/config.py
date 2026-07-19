"""
Central configuration for AppPulse Analytics backend.
All values are overridable via environment variables (see docker-compose.yml).
"""
import json
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- Core ---
    APP_NAME: str = "AppPulse Analytics"
    ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://apppulse:apppulse@postgres:5432/apppulse"

    # --- Cache ---
    REDIS_URL: str = "redis://redis:6379/0"

    # --- Scraping / ingestion ---
    # How often (seconds) the background scheduler re-polls each tracked app.
    # Keep this reasonable - hitting Apple/Google too aggressively will get you
    # rate-limited or IP-blocked. 15 minutes is a sane default for a free,
    # scraping-based pipeline.
    REFRESH_INTERVAL_SECONDS: int = 900
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    SCRAPER_TIMEOUT_SECONDS: int = 15
    SCRAPER_MAX_RETRIES: int = 3

    # Runs the APScheduler polling loop inside the web process. Leave this
    # True for a single-service deploy (e.g. Render's free/Starter web
    # service). Set to False only if you're running the scheduler as a
    # separate dedicated worker service (see backend/app/worker_main.py) -
    # running both at once would double-poll every app.
    ENABLE_EMBEDDED_SCHEDULER: bool = True

    # --- CORS ---
    # Deliberately typed as a plain string, not list[str]: pydantic-settings
    # tries to JSON-decode ANY env var mapped to a list/collection field
    # before validation even runs, which crashes the app on startup if
    # someone pastes a bare URL or a comma-separated value into a platform's
    # env var box (e.g. Render's dashboard) instead of strict JSON. Storing
    # this as a string and parsing it ourselves in `parsed_cors_origins()`
    # sidesteps that entirely - accepts any of:
    #   CORS_ORIGINS=https://your-site.netlify.app
    #   CORS_ORIGINS=https://your-site.netlify.app,https://staging.example.com
    #   CORS_ORIGINS=["https://your-site.netlify.app"]
    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

    def parsed_cors_origins(self) -> list[str]:
        v = self.CORS_ORIGINS.strip()
        if not v:
            return []
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(o).strip() for o in parsed]
            except json.JSONDecodeError:
                pass
            v = v.strip("[]")
        return [origin.strip().strip('"').strip("'") for origin in v.split(",") if origin.strip()]

    def normalized_database_url(self) -> str:
        """
        Render (and most managed Postgres providers) hand you a URL like
        `postgres://user:pass@host/db` or `postgresql://...` with no driver
        specified. SQLAlchemy needs the psycopg driver named explicitly -
        this rewrites the scheme without requiring you to hand-edit
        whatever the platform injects into DATABASE_URL.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
