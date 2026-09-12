from datetime import UTC, datetime
from typing import Any

from pymongo.errors import DuplicateKeyError

from hbms.db.mongo import mongo_manager


class IdempotencyRepository:
    @staticmethod
    async def get(customer_id: str, endpoint: str, idempotency_key: str) -> dict[str, Any] | None:
        return await mongo_manager.db["idempotency_records"].find_one(
            {
                "customer_id": customer_id,
                "endpoint": endpoint,
                "idempotency_key": idempotency_key,
            }
        )

    @staticmethod
    async def save(
        *,
        customer_id: str,
        endpoint: str,
        idempotency_key: str,
        response_body: dict[str, Any],
    ) -> None:
        document = {
            "customer_id": customer_id,
            "endpoint": endpoint,
            "idempotency_key": idempotency_key,
            "response_body": response_body,
            "created_at": datetime.now(UTC),
        }
        try:
            await mongo_manager.db["idempotency_records"].insert_one(document)
        except DuplicateKeyError:
            return
