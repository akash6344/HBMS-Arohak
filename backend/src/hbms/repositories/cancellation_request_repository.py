from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument

from pymongo.errors import DuplicateKeyError

from hbms.core.object_ids import parse_object_id
from hbms.db.mongo import mongo_manager
from hbms.domain.enums import CancellationRequestStatus


class CancellationRequestConflictError(Exception):
    pass


class CancellationRequestRepository:
    @staticmethod
    async def create(
        *,
        booking_id: str,
        organization_id: str,
        hotel_id: str,
        requested_by: str,
        reason: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        document = {
            "booking_id": parse_object_id(booking_id, field_name="booking_id"),
            "organization_id": parse_object_id(organization_id, field_name="organization_id"),
            "hotel_id": parse_object_id(hotel_id, field_name="hotel_id"),
            "requested_by": parse_object_id(requested_by, field_name="requested_by"),
            "reason": reason.strip(),
            "status": CancellationRequestStatus.PENDING.value,
            "reviewed_by": None,
            "reviewed_at": None,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await mongo_manager.db["cancellation_requests"].insert_one(document)
        except DuplicateKeyError as exc:
            raise CancellationRequestConflictError from exc
        document["_id"] = result.inserted_id
        return document

    @staticmethod
    async def get_by_id(request_id: str) -> dict[str, Any] | None:
        return await mongo_manager.db["cancellation_requests"].find_one(
            {"_id": parse_object_id(request_id, field_name="request_id")}
        )

    @staticmethod
    async def get_pending_for_booking(booking_id: str) -> dict[str, Any] | None:
        return await mongo_manager.db["cancellation_requests"].find_one(
            {
                "booking_id": parse_object_id(booking_id, field_name="booking_id"),
                "status": CancellationRequestStatus.PENDING.value,
            }
        )

    @staticmethod
    async def list_for_scope(
        *,
        organization_ids: list[str] | None = None,
        hotel_ids: list[str] | None = None,
        status_value: CancellationRequestStatus | None = None,
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
                "$in": [parse_object_id(hotel_id, field_name="hotel_id") for hotel_id in hotel_ids]
            }
        if status_value is not None:
            query["status"] = status_value.value

        cursor = mongo_manager.db["cancellation_requests"].find(query).sort("created_at", -1)
        return [document async for document in cursor]

    @staticmethod
    async def list_for_requester(
        requested_by: str,
        *,
        status_value: CancellationRequestStatus | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {
            "requested_by": parse_object_id(requested_by, field_name="requested_by"),
        }
        if status_value is not None:
            query["status"] = status_value.value
        cursor = mongo_manager.db["cancellation_requests"].find(query).sort("created_at", -1)
        return [document async for document in cursor]

    @staticmethod
    async def mark_reviewed(
        request_id: str,
        *,
        status_value: CancellationRequestStatus,
        reviewed_by: str,
    ) -> dict[str, Any] | None:
        return await mongo_manager.db["cancellation_requests"].find_one_and_update(
            {
                "_id": parse_object_id(request_id, field_name="request_id"),
                "status": CancellationRequestStatus.PENDING.value,
            },
            {
                "$set": {
                    "status": status_value.value,
                    "reviewed_by": parse_object_id(reviewed_by, field_name="reviewed_by"),
                    "reviewed_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
