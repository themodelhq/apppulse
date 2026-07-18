"""
Standalone worker entrypoint.

Use this instead of the embedded scheduler when you want polling to run on
a dedicated process - e.g. a Render "Background Worker" service - so it
never depends on whether the web service has received an HTTP request
recently.

Run with: python -m app.worker_main

If you use this, set ENABLE_EMBEDDED_SCHEDULER=false on the web service so
you don't end up polling every app twice on the same interval.
"""
import asyncio
import logging

from app.database import Base, engine
from app.scheduler import start_scheduler, scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apppulse.worker")


async def main() -> None:
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    logger.info("Worker started - polling on the configured refresh interval.")
    try:
        # Keep the event loop alive forever; APScheduler's AsyncIOScheduler
        # runs its jobs on this same loop.
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
