import hashlib
from datetime import UTC, datetime
from typing import Any

from hbms.core.object_ids import parse_object_id
from hbms.db.mongo import mongo_manager


class RefreshTokenRepository:
    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    async def create(*, user_id: str, token: str, expires_at: datetime) -> None:
        await mongo_manager.db["refresh_tokens"].insert_one(
            {
                "user_id": parse_object_id(user_id, field_name="user_id"),
                "token_hash": RefreshTokenRepository.hash_token(token),
                "expires_at": expires_at,
                "revoked_at": None,
                "created_at": datetime.now(UTC),
            }
        )

    @staticmethod
    async def get_active(token: str) -> dict[str, Any] | None:
        return await mongo_manager.db["refresh_tokens"].find_one(
            {
                "token_hash": RefreshTokenRepository.hash_token(token),
                "revoked_at": None,
                "expires_at": {"$gt": datetime.now(UTC)},
            }
        )

    @staticmethod
    async def revoke(token: str) -> None:
        await mongo_manager.db["refresh_tokens"].update_one(
            {"token_hash": RefreshTokenRepository.hash_token(token)},
            {"$set": {"revoked_at": datetime.now(UTC)}},
        )

    @staticmethod
    async def revoke_all_for_user(user_id: str) -> None:
        await mongo_manager.db["refresh_tokens"].update_many(
            {
                "user_id": parse_object_id(user_id, field_name="user_id"),
                "revoked_at": None,
            },
            {"$set": {"revoked_at": datetime.now(UTC)}},
        )
