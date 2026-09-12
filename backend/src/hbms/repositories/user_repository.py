from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from hbms.core.object_ids import parse_object_id
from hbms.db.mongo import mongo_manager
from hbms.domain.enums import Role
from hbms.domain.schemas import UserCreate


class UserAlreadyExistsError(Exception):
    pass


class UserRepository:
    @staticmethod
    async def create_customer(user: UserCreate, password_hash: str) -> dict[str, Any]:
        return await UserRepository._create_user(
            name=user.name,
            email=str(user.email),
            password_hash=password_hash,
            role=Role.CUSTOMER,
            organization_ids=[],
            hotel_ids=[],
        )

    @staticmethod
    async def create_staff_user(
        *,
        name: str,
        email: str,
        password_hash: str,
        role: Role,
        organization_ids: list[str],
        hotel_ids: list[str],
    ) -> dict[str, Any]:
        return await UserRepository._create_user(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role,
            organization_ids=organization_ids,
            hotel_ids=hotel_ids,
        )

    @staticmethod
    async def _create_user(
        *,
        name: str,
        email: str,
        password_hash: str,
        role: Role,
        organization_ids: list[str],
        hotel_ids: list[str],
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        document = {
            "name": name.strip(),
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "role": role.value,
            "organization_ids": [
                parse_object_id(organization_id, field_name="organization_id")
                for organization_id in organization_ids
            ],
            "hotel_ids": [parse_object_id(hotel_id, field_name="hotel_id") for hotel_id in hotel_ids],
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await mongo_manager.db["users"].insert_one(document)
        except DuplicateKeyError as exc:
            raise UserAlreadyExistsError from exc
        document["_id"] = result.inserted_id
        return document

    @staticmethod
    async def get_by_email(email: str) -> dict[str, Any] | None:
        return await mongo_manager.db["users"].find_one({"email": email.lower().strip()})

    @staticmethod
    async def get_by_id(user_id: str) -> dict[str, Any] | None:
        return await mongo_manager.db["users"].find_one(
            {"_id": parse_object_id(user_id, field_name="user_id")}
        )

    @staticmethod
    async def assign_hotels(user_id: str, hotel_ids: list[str]) -> dict[str, Any] | None:
        return await mongo_manager.db["users"].find_one_and_update(
            {"_id": parse_object_id(user_id, field_name="user_id")},
            {
                "$set": {
                    "hotel_ids": [
                        parse_object_id(hotel_id, field_name="hotel_id") for hotel_id in hotel_ids
                    ],
                    "updated_at": datetime.now(UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    @staticmethod
    async def find_ids_by_email_or_name(query: str) -> list[Any]:
        cursor = mongo_manager.db["users"].find(
            {
                "$or": [
                    {"email": {"$regex": query, "$options": "i"}},
                    {"name": {"$regex": query, "$options": "i"}},
                ]
            },
            {"_id": 1},
        )
        return [document["_id"] async for document in cursor]
