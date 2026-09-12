from collections.abc import Sequence
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING
from pymongo.operations import IndexModel

from hbms.core.config import get_settings


class MongoManager:
    def __init__(self) -> None:
        self._client: AsyncIOMotorClient[Any] | None = None
        self._database: AsyncIOMotorDatabase[Any] | None = None

    @property
    def client(self) -> AsyncIOMotorClient[Any]:
        if self._client is None:
            msg = "Mongo client is not initialized."
            raise RuntimeError(msg)
        return self._client

    @property
    def db(self) -> AsyncIOMotorDatabase[Any]:
        if self._database is None:
            msg = "Mongo database is not initialized."
            raise RuntimeError(msg)
        return self._database

    async def connect(self) -> None:
        settings = get_settings()
        self._client = AsyncIOMotorClient(settings.mongodb_uri)
        self._database = self._client[settings.mongodb_database]
        await self._ensure_indexes()

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self._database = None

    async def _ensure_indexes(self) -> None:
        if self._database is None:
            msg = "Cannot create indexes before database initialization."
            raise RuntimeError(msg)

        await self._create_indexes(
            "users",
            [
                IndexModel([("email", ASCENDING)], unique=True, name="uq_users_email"),
                IndexModel([("role", ASCENDING)], name="ix_users_role"),
            ],
        )
        await self._create_indexes(
            "organizations",
            [IndexModel([("status", ASCENDING)], name="ix_organizations_status")],
        )
        await self._create_indexes(
            "hotels",
            [
                IndexModel(
                    [("organization_id", ASCENDING), ("city", ASCENDING), ("status", ASCENDING)],
                    name="ix_hotels_org_city_status",
                ),
                IndexModel(
                    [("organization_id", ASCENDING), ("name", ASCENDING)],
                    name="ix_hotels_org_name",
                ),
            ],
        )
        await self._create_indexes(
            "rooms",
            [
                IndexModel(
                    [("organization_id", ASCENDING), ("hotel_id", ASCENDING), ("room_number", ASCENDING)],
                    unique=True,
                    name="uq_rooms_org_hotel_room_number",
                ),
                IndexModel(
                    [
                        ("organization_id", ASCENDING),
                        ("hotel_id", ASCENDING),
                        ("is_active", ASCENDING),
                        ("availability_status", ASCENDING),
                        ("capacity", ASCENDING),
                    ],
                    name="ix_rooms_search_filter",
                ),
            ],
        )
        await self._create_indexes(
            "bookings",
            [
                IndexModel([("booking_ref", ASCENDING)], unique=True, name="uq_bookings_booking_ref"),
                IndexModel(
                    [
                        ("organization_id", ASCENDING),
                        ("hotel_id", ASCENDING),
                        ("customer_id", ASCENDING),
                        ("status", ASCENDING),
                        ("check_in_date", ASCENDING),
                    ],
                    name="ix_bookings_customer_scope",
                ),
                IndexModel(
                    [("room_id", ASCENDING), ("check_in_date", ASCENDING), ("check_out_date", ASCENDING)],
                    name="ix_bookings_room_dates",
                ),
            ],
        )
        await self._create_indexes(
            "room_inventory_days",
            [
                IndexModel(
                    [
                        ("organization_id", ASCENDING),
                        ("hotel_id", ASCENDING),
                        ("room_id", ASCENDING),
                        ("date", ASCENDING),
                    ],
                    unique=True,
                    name="uq_room_inventory_day_lock",
                )
            ],
        )
        await self._create_indexes(
            "idempotency_records",
            [
                IndexModel(
                    [
                        ("customer_id", ASCENDING),
                        ("endpoint", ASCENDING),
                        ("idempotency_key", ASCENDING),
                    ],
                    unique=True,
                    name="uq_idempotency_by_customer_endpoint_key",
                )
            ],
        )
        await self._create_indexes(
            "cancellation_requests",
            [
                IndexModel(
                    [("booking_id", ASCENDING), ("status", ASCENDING)],
                    name="ix_cancellation_requests_booking_status",
                ),
                IndexModel(
                    [("organization_id", ASCENDING), ("hotel_id", ASCENDING), ("status", ASCENDING)],
                    name="ix_cancellation_requests_scope",
                ),
                IndexModel(
                    [("booking_id", ASCENDING)],
                    unique=True,
                    partialFilterExpression={"status": "PENDING"},
                    name="uq_cancellation_requests_pending_booking",
                ),
                IndexModel(
                    [("requested_by", ASCENDING), ("status", ASCENDING)],
                    name="ix_cancellation_requests_requester_status",
                ),
            ],
        )
        await self._create_indexes(
            "refresh_tokens",
            [
                IndexModel([("token_hash", ASCENDING)], unique=True, name="uq_refresh_tokens_hash"),
                IndexModel([("user_id", ASCENDING), ("revoked_at", ASCENDING)], name="ix_refresh_tokens_user"),
            ],
        )
        await self._create_indexes(
            "hotel_documents",
            [
                IndexModel(
                    [
                        ("organization_id", ASCENDING),
                        ("hotel_id", ASCENDING),
                        ("source_file", ASCENDING),
                    ],
                    unique=True,
                    name="uq_hotel_documents_org_hotel_source",
                ),
                IndexModel(
                    [("organization_id", ASCENDING), ("hotel_id", ASCENDING)],
                    name="ix_hotel_documents_scope",
                ),
            ],
        )
        await self._create_indexes(
            "hotel_document_chunks",
            [
                IndexModel(
                    [("organization_id", ASCENDING), ("hotel_id", ASCENDING), ("chunk_index", ASCENDING)],
                    name="ix_hotel_chunks_scope_order",
                ),
                IndexModel(
                    [("document_id", ASCENDING), ("chunk_index", ASCENDING)],
                    name="ix_hotel_chunks_document",
                ),
            ],
        )

    async def _create_indexes(self, collection_name: str, indexes: Sequence[IndexModel]) -> None:
        if self._database is None:
            msg = "Cannot create index: Mongo database is not initialized."
            raise RuntimeError(msg)
        if not indexes:
            return
        collection = self._database[collection_name]
        await collection.create_indexes(indexes)


mongo_manager = MongoManager()
