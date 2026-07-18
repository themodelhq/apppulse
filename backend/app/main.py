import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import apps, dashboard
from app.scheduler import start_scheduler, scheduler
from app.websocket_manager import manager

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: auto-create tables. Use Alembic migrations in production
    # (see backend/alembic/ - not included in this first pass, noted in README).
    Base.metadata.create_all(bind=engine)
    if settings.ENABLE_EMBEDDED_SCHEDULER:
        start_scheduler()
    yield
    if settings.ENABLE_EMBEDDED_SCHEDULER:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Real-time app store intelligence - download estimates, rankings, and alerts.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(apps.router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect inbound client messages, but need to keep the
            # receive loop alive to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
