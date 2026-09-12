from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hbms.api.router import api_router
from hbms.core.config import get_settings
from hbms.core.logging import configure_logging
from hbms.db.mongo import mongo_manager
from hbms.jobs.booking_status import complete_past_checkouts
from hbms.jobs.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)
settings = get_settings()
configure_logging(settings.app_debug)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await mongo_manager.connect()
    # Run once on boot so statuses are current before the first cron tick.
    await complete_past_checkouts()
    start_scheduler(cron=settings.booking_completion_cron)
    try:
        yield
    finally:
        stop_scheduler()
        await mongo_manager.disconnect()


app = FastAPI(title=settings.app_name, debug=settings.app_debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
