from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from hbms.db.mongo import mongo_manager


class HotelDocumentRepository:
    @staticmethod
    async def create_document(
        *,
        organization_id: str,
        hotel_id: str,
        source_file: str,
        version: str,
        uploaded_by: str | None,
        page_count: int,
        chunk_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        document = {
            "organization_id": organization_id,
            "hotel_id": hotel_id,
            "source_file": source_file,
            "version": version,
            "uploaded_by": uploaded_by,
            "uploaded_at": now,
            "page_count": page_count,
            "chunk_count": chunk_count,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        result = await mongo_manager.db.hotel_documents.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    @staticmethod
    async def find_by_source(
        *,
        organization_id: str,
        hotel_id: str,
        source_file: str,
    ) -> dict[str, Any] | None:
        return await mongo_manager.db.hotel_documents.find_one(
            {
                "organization_id": organization_id,
                "hotel_id": hotel_id,
                "source_file": source_file,
            }
        )

    @staticmethod
    async def delete_document_and_chunks(document_id: str) -> None:
        await mongo_manager.db.hotel_document_chunks.delete_many({"document_id": document_id})
        await mongo_manager.db.hotel_documents.delete_one({"_id": ObjectId(document_id)})

    @staticmethod
    async def insert_chunks(chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            return
        now = datetime.now(UTC)
        for chunk in chunks:
            chunk.setdefault("created_at", now)
        await mongo_manager.db.hotel_document_chunks.insert_many(chunks)

    @staticmethod
    async def list_chunks_for_hotel(
        *,
        organization_id: str,
        hotel_id: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        cursor = (
            mongo_manager.db.hotel_document_chunks.find(
                {"organization_id": organization_id, "hotel_id": hotel_id}
            )
            .sort("chunk_index", 1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    @staticmethod
    async def list_hotels_with_documents() -> list[dict[str, Any]]:
        """Return distinct hotel scopes that have at least one ingested document."""
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "organization_id": "$organization_id",
                        "hotel_id": "$hotel_id",
                    },
                    "source_file": {"$first": "$source_file"},
                    "chunk_count": {"$first": "$chunk_count"},
                    "uploaded_at": {"$first": "$uploaded_at"},
                }
            },
            {"$sort": {"uploaded_at": -1}},
        ]
        rows = await mongo_manager.db.hotel_documents.aggregate(pipeline).to_list(length=200)
        result: list[dict[str, Any]] = []
        for row in rows:
            key = row.get("_id") or {}
            organization_id = key.get("organization_id")
            hotel_id = key.get("hotel_id")
            if not organization_id or not hotel_id:
                continue
            hotel = await mongo_manager.db.hotels.find_one({"_id": ObjectId(str(hotel_id))})
            if hotel is None:
                continue
            result.append(
                {
                    "organization_id": str(organization_id),
                    "hotel_id": str(hotel_id),
                    "hotel_name": hotel.get("name"),
                    "city": hotel.get("city"),
                    "source_file": row.get("source_file"),
                    "chunk_count": row.get("chunk_count", 0),
                }
            )
        return result
