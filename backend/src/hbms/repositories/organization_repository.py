from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument

from hbms.core.object_ids import parse_object_id
from hbms.db.mongo import mongo_manager
from hbms.domain.enums import EntityStatus
from hbms.domain.schemas import OrganizationCreate, OrganizationUpdate


class OrganizationRepository:
    @staticmethod
    async def create(payload: OrganizationCreate) -> dict[str, Any]:
        now = datetime.now(UTC)
        document = {
            "name": payload.name.strip(),
            "status": EntityStatus.ACTIVE.value,
            "created_at": now,
            "updated_at": now,
        }
        result = await mongo_manager.db["organizations"].insert_one(document)
        document["_id"] = result.inserted_id
        return document

    @staticmethod
    async def list_all() -> list[dict[str, Any]]:
        cursor = mongo_manager.db["organizations"].find().sort("created_at", -1)
        return [document async for document in cursor]

    @staticmethod
    async def get_by_id(organization_id: str) -> dict[str, Any] | None:
        return await mongo_manager.db["organizations"].find_one(
            {"_id": parse_object_id(organization_id, field_name="organization_id")}
        )

    @staticmethod
    async def update(organization_id: str, payload: OrganizationUpdate) -> dict[str, Any] | None:
        updates = payload.model_dump(exclude_none=True)
        if "name" in updates and isinstance(updates["name"], str):
            updates["name"] = updates["name"].strip()
        if "status" in updates:
            updates["status"] = updates["status"].value

        if not updates:
            return await OrganizationRepository.get_by_id(organization_id)

        updates["updated_at"] = datetime.now(UTC)
        return await mongo_manager.db["organizations"].find_one_and_update(
            {"_id": parse_object_id(organization_id, field_name="organization_id")},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
