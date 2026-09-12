from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from pymongo import ReturnDocument
from pymongo.errors import BulkWriteError, DuplicateKeyError

from hbms.core.object_ids import parse_object_id
from hbms.db.mongo import mongo_manager
from hbms.domain.enums import BookingStatus

_DUPLICATE_KEY_CODE = 11000


class BookingConflictError(Exception):
    pass


def _is_duplicate_key_error(exc: BulkWriteError) -> bool:
    write_errors = exc.details.get("writeErrors", []) if exc.details else []
    return any(error.get("code") == _DUPLICATE_KEY_CODE for error in write_errors)


class BookingRepository:
    @staticmethod
    def iterate_stay_dates(check_in_date: date, check_out_date: date) -> list[date]:
        nights = (check_out_date - check_in_date).days
        return [check_in_date + timedelta(days=offset) for offset in range(nights)]

    @staticmethod
    def compute_cancellation_deadline(check_in_date: date, hotel_timezone: str) -> datetime:
        timezone = ZoneInfo(hotel_timezone)
        local_deadline = datetime.combine(check_in_date - timedelta(days=1), time(23, 59, 59), tzinfo=timezone)
        return local_deadline.astimezone(UTC)

    @staticmethod
    def compute_total_amount(nightly_rate: Decimal, check_in_date: date, check_out_date: date) -> Decimal:
        nights = (check_out_date - check_in_date).days
        return nightly_rate * nights

    @staticmethod
    async def find_conflicting_room_ids(
        *,
        room_ids: list[Any],
        check_in_date: date,
        check_out_date: date,
    ) -> set[str]:
        if not room_ids:
            return set()
        stay_dates = BookingRepository.iterate_stay_dates(check_in_date, check_out_date)
        cursor = mongo_manager.db["room_inventory_days"].find(
            {
                "room_id": {"$in": room_ids},
                "date": {"$in": [day.isoformat() for day in stay_dates]},
            },
            {"room_id": 1},
        )
        return {str(document["room_id"]) async for document in cursor}

    @staticmethod
    async def create_with_day_locks(
        *,
        organization_id: str,
        hotel_id: str,
        room_id: str,
        customer_id: str,
        check_in_date: date,
        check_out_date: date,
        guest_count: int,
        nightly_rate: Decimal,
        currency: str,
        hotel_timezone: str,
        booking_ref: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        stay_dates = BookingRepository.iterate_stay_dates(check_in_date, check_out_date)
        organization_oid = parse_object_id(organization_id, field_name="organization_id")
        hotel_oid = parse_object_id(hotel_id, field_name="hotel_id")
        room_oid = parse_object_id(room_id, field_name="room_id")
        customer_oid = parse_object_id(customer_id, field_name="customer_id")

        booking_document = {
            "booking_ref": booking_ref,
            "organization_id": organization_oid,
            "hotel_id": hotel_oid,
            "room_id": room_oid,
            "customer_id": customer_oid,
            "check_in_date": check_in_date.isoformat(),
            "check_out_date": check_out_date.isoformat(),
            "guest_count": guest_count,
            "booking_date": now,
            "nightly_rate_snapshot": format(nightly_rate, "f"),
            "currency": currency,
            "total_amount": format(
                BookingRepository.compute_total_amount(nightly_rate, check_in_date, check_out_date),
                "f",
            ),
            "status": BookingStatus.CONFIRMED.value,
            "cancellation_deadline_at": BookingRepository.compute_cancellation_deadline(
                check_in_date,
                hotel_timezone,
            ),
            "created_at": now,
            "updated_at": now,
        }

        client = mongo_manager.client
        async with await client.start_session() as session:
            try:
                async with session.start_transaction():
                    day_locks = [
                        {
                            "organization_id": organization_oid,
                            "hotel_id": hotel_oid,
                            "room_id": room_oid,
                            "date": day.isoformat(),
                            "created_at": now,
                        }
                        for day in stay_dates
                    ]
                    if day_locks:
                        await mongo_manager.db["room_inventory_days"].insert_many(
                            day_locks,
                            session=session,
                            ordered=True,
                        )
                    result = await mongo_manager.db["bookings"].insert_one(
                        booking_document,
                        session=session,
                    )
                    booking_document["_id"] = result.inserted_id
            except DuplicateKeyError as exc:
                raise BookingConflictError from exc
            except BulkWriteError as exc:
                if _is_duplicate_key_error(exc):
                    raise BookingConflictError from exc
                raise

        return booking_document

    @staticmethod
    async def get_by_id(booking_id: str) -> dict[str, Any] | None:
        return await mongo_manager.db["bookings"].find_one(
            {"_id": parse_object_id(booking_id, field_name="booking_id")}
        )

    @staticmethod
    async def list_for_customer(customer_id: str) -> list[dict[str, Any]]:
        cursor = (
            mongo_manager.db["bookings"]
            .find({"customer_id": parse_object_id(customer_id, field_name="customer_id")})
            .sort("booking_date", -1)
        )
        return [document async for document in cursor]

    @staticmethod
    async def cancel(booking_id: str) -> dict[str, Any] | None:
        booking = await BookingRepository.get_by_id(booking_id)
        if booking is None:
            return None
        if booking["status"] == BookingStatus.CANCELLED.value:
            return booking

        now = datetime.now(UTC)
        client = mongo_manager.client
        async with await client.start_session() as session:
            async with session.start_transaction():
                updated = await mongo_manager.db["bookings"].find_one_and_update(
                    {
                        "_id": parse_object_id(booking_id, field_name="booking_id"),
                        "status": BookingStatus.CONFIRMED.value,
                    },
                    {
                        "$set": {
                            "status": BookingStatus.CANCELLED.value,
                            "updated_at": now,
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )
                if updated is None:
                    return await BookingRepository.get_by_id(booking_id)

                stay_dates = BookingRepository.iterate_stay_dates(
                    date.fromisoformat(updated["check_in_date"]),
                    date.fromisoformat(updated["check_out_date"]),
                )
                await mongo_manager.db["room_inventory_days"].delete_many(
                    {
                        "room_id": updated["room_id"],
                        "date": {"$in": [day.isoformat() for day in stay_dates]},
                    },
                    session=session,
                )
                return updated

    @staticmethod
    async def list_for_staff(
        *,
        organization_ids: list[str] | None = None,
        hotel_ids: list[str] | None = None,
        status_value: BookingStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        hotel_id: str | None = None,
        room_id: str | None = None,
        customer_ids: list[Any] | None = None,
        booking_ref: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if organization_ids is not None:
            query["organization_id"] = {
                "$in": [
                    parse_object_id(organization_id, field_name="organization_id")
                    for organization_id in organization_ids
                ]
            }
        if hotel_ids is not None:
            query["hotel_id"] = {
                "$in": [parse_object_id(item, field_name="hotel_id") for item in hotel_ids]
            }
        if hotel_id:
            query["hotel_id"] = parse_object_id(hotel_id, field_name="hotel_id")
        if room_id:
            query["room_id"] = parse_object_id(room_id, field_name="room_id")
        if status_value is not None:
            query["status"] = status_value.value
        if booking_ref:
            query["booking_ref"] = {"$regex": booking_ref, "$options": "i"}
        if customer_ids is not None:
            query["customer_id"] = {"$in": customer_ids}
        if date_from or date_to:
            date_filter: dict[str, Any] = {}
            if date_from:
                date_filter["$gte"] = date_from.isoformat()
            if date_to:
                date_filter["$lte"] = date_to.isoformat()
            query["check_in_date"] = date_filter

        cursor = (
            mongo_manager.db["bookings"]
            .find(query)
            .sort("booking_date", -1)
            .skip(max(skip, 0))
            .limit(min(max(limit, 1), 100))
        )
        return [document async for document in cursor]

    @staticmethod
    async def complete_past_checkouts() -> int:
        today = date.today().isoformat()
        result = await mongo_manager.db["bookings"].update_many(
            {
                "status": BookingStatus.CONFIRMED.value,
                "check_out_date": {"$lte": today},
            },
            {
                "$set": {
                    "status": BookingStatus.COMPLETED.value,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return int(result.modified_count)
