import logging

from hbms.repositories.booking_repository import BookingRepository

logger = logging.getLogger(__name__)

JOB_ID = "complete_past_checkouts"


async def complete_past_checkouts() -> int:
    completed = await BookingRepository.complete_past_checkouts()
    if completed:
        logger.info("Marked %s bookings as COMPLETED", completed)
    else:
        logger.debug("No bookings needed COMPLETED transition")
    return completed
