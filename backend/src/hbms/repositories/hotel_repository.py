from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument

from hbms.core.object_ids import parse_object_id
from hbms.db.mongo import mongo_manager
from hbms.domain.enums import EntityStatus
from hbms.domain.schemas import HotelCreate, HotelUpdate


class HotelRepository:
    @staticmethod
    async def create(organization_id: str, payload: HotelCreate) -> dict[str, Any]:
        now = datetime.now(UTC)
        document = {
            "organization_id": parse_object_id(organization_id, field_name="organization_id"),
            "name": payload.name.strip(),
            "address": payload.address.strip(),
            "city": payload.city.strip(),
            "description": payload.description.strip(),
            "contact_number": payload.contact_number.strip(),
            "email": str(payload.email).lower().strip(),
            "timezone": payload.timezone.strip(),
            "status": EntityStatus.ACTIVE.value,
            "created_at": now,
            "updated_at": now,
        }
        result = await mongo_manager.db["hotels"].insert_one(document)
        document["_id"] = result.inserted_id
        return document

    @staticmethod
    async def list_by_organization(organization_id: str) -> list[dict[str, Any]]:
        cursor = (
            mongo_manager.db["hotels"]
            .find({"organization_id": parse_object_id(organization_id, field_name="organization_id")})
            .sort("created_at", -1)
        )
        return [document async for document in cursor]

    @staticmethod
    async def list_active(*, city: str | None = None, organization_id: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"status": EntityStatus.ACTIVE.value}
        if city:
            query["city"] = {"$regex": f"^{city.strip()}$", "$options": "i"}
        if organization_id:
            query["organization_id"] = parse_object_id(organization_id, field_name="organization_id")
        cursor = mongo_manager.db["hotels"].find(query).sort("name", 1)
        return [document async for document in cursor]

    @staticmethod
    async def get_by_id(hotel_id: str) -> dict[str, Any] | None:
        return await mongo_manager.db["hotels"].find_one(
            {"_id": parse_object_id(hotel_id, field_name="hotel_id")}
        )

    @staticmethod
    async def update(hotel_id: str, payload: HotelUpdate) -> dict[str, Any] | None:
        updates = payload.model_dump(exclude_none=True)
        for key in ("name", "address", "city", "description", "contact_number", "timezone"):
            if key in updates and isinstance(updates[key], str):
                updates[key] = updates[key].strip()
        if "email" in updates:
            updates["email"] = str(updates["email"]).lower().strip()
        if "status" in updates:
            updates["status"] = updates["status"].value

        if not updates:
            return await HotelRepository.get_by_id(hotel_id)

        updates["updated_at"] = datetime.now(UTC)
        return await mongo_manager.db["hotels"].find_one_and_update(
            {"_id": parse_object_id(hotel_id, field_name="hotel_id")},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
