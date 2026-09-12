from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from hbms.core.object_ids import parse_object_id
from hbms.db.mongo import mongo_manager
from hbms.domain.enums import RoomAvailabilityStatus
from hbms.domain.schemas import RoomCreate, RoomUpdate


class RoomNumberConflictError(Exception):
    pass


class RoomRepository:
    @staticmethod
    def _serialize_price(value: Decimal) -> str:
        return format(value, "f")

    @staticmethod
    async def create(
        *,
        organization_id: str,
        hotel_id: str,
        payload: RoomCreate,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        document = {
            "organization_id": parse_object_id(organization_id, field_name="organization_id"),
            "hotel_id": parse_object_id(hotel_id, field_name="hotel_id"),
            "room_number": payload.room_number.strip(),
            "room_type": payload.room_type.strip(),
            "capacity": payload.capacity,
            "price_per_night": RoomRepository._serialize_price(payload.price_per_night),
            "currency": payload.currency,
            "availability_status": payload.availability_status.value,
            "is_active": True,
            "description": payload.description.strip(),
            "amenities": payload.amenities,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await mongo_manager.db["rooms"].insert_one(document)
        except DuplicateKeyError as exc:
            raise RoomNumberConflictError from exc
        document["_id"] = result.inserted_id
        return document

    @staticmethod
    async def list_by_hotel(organization_id: str, hotel_id: str) -> list[dict[str, Any]]:
        cursor = (
            mongo_manager.db["rooms"]
            .find(
                {
                    "organization_id": parse_object_id(organization_id, field_name="organization_id"),
                    "hotel_id": parse_object_id(hotel_id, field_name="hotel_id"),
                }
            )
            .sort("room_number", 1)
        )
        return [document async for document in cursor]

    @staticmethod
    async def get_by_id(
        room_id: str,
        *,
        organization_id: str | None = None,
        hotel_id: str | None = None,
    ) -> dict[str, Any] | None:
        query: dict[str, Any] = {"_id": parse_object_id(room_id, field_name="room_id")}
        if organization_id:
            query["organization_id"] = parse_object_id(organization_id, field_name="organization_id")
        if hotel_id:
            query["hotel_id"] = parse_object_id(hotel_id, field_name="hotel_id")
        return await mongo_manager.db["rooms"].find_one(query)

    @staticmethod
    async def update(
        room_id: str,
        *,
        organization_id: str,
        hotel_id: str,
        payload: RoomUpdate,
    ) -> dict[str, Any] | None:
        updates = payload.model_dump(exclude_none=True)
        for key in ("room_number", "room_type", "description"):
            if key in updates and isinstance(updates[key], str):
                updates[key] = updates[key].strip()
        if "price_per_night" in updates:
            updates["price_per_night"] = RoomRepository._serialize_price(updates["price_per_night"])
        if "availability_status" in updates:
            updates["availability_status"] = updates["availability_status"].value

        if not updates:
            return await RoomRepository.get_by_id(
                room_id,
                organization_id=organization_id,
                hotel_id=hotel_id,
            )

        updates["updated_at"] = datetime.now(UTC)
        try:
            return await mongo_manager.db["rooms"].find_one_and_update(
                {
                    "_id": parse_object_id(room_id, field_name="room_id"),
                    "organization_id": parse_object_id(organization_id, field_name="organization_id"),
                    "hotel_id": parse_object_id(hotel_id, field_name="hotel_id"),
                },
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise RoomNumberConflictError from exc

    @staticmethod
    async def deactivate(
        room_id: str,
        *,
        organization_id: str,
        hotel_id: str,
    ) -> dict[str, Any] | None:
        return await mongo_manager.db["rooms"].find_one_and_update(
            {
                "_id": parse_object_id(room_id, field_name="room_id"),
                "organization_id": parse_object_id(organization_id, field_name="organization_id"),
                "hotel_id": parse_object_id(hotel_id, field_name="hotel_id"),
            },
            {
                "$set": {
                    "is_active": False,
                    "availability_status": RoomAvailabilityStatus.UNAVAILABLE.value,
                    "updated_at": datetime.now(UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    @staticmethod
    async def list_search_candidates(
        *,
        guest_count: int,
        hotel_ids: list[Any],
    ) -> list[dict[str, Any]]:
        if not hotel_ids:
            return []
        cursor = mongo_manager.db["rooms"].find(
            {
                "hotel_id": {"$in": hotel_ids},
                "is_active": True,
                "availability_status": RoomAvailabilityStatus.AVAILABLE.value,
                "capacity": {"$gte": guest_count},
            }
        )
        return [document async for document in cursor]
