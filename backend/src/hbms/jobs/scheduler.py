import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from hbms.jobs.booking_status import JOB_ID, complete_past_checkouts

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler(*, cron: str) -> None:
    if scheduler.running:
        return

    trigger = CronTrigger.from_crontab(cron)
    scheduler.add_job(
        complete_past_checkouts,
        trigger=trigger,
        id=JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Background scheduler started (job=%s cron=%r)", JOB_ID, cron)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
