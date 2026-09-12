from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from hbms.core.config import get_settings
from hbms.domain.schemas import AuthenticatedPrincipal


def _create_token(claims: dict[str, Any], expires_delta: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(principal: AuthenticatedPrincipal) -> str:
    settings = get_settings()
    claims = {
        "sub": principal.user_id,
        "role": principal.role.value,
        "organization_ids": principal.organization_ids,
        "hotel_ids": principal.hotel_ids,
        "type": "access",
    }
    return _create_token(claims, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(principal: AuthenticatedPrincipal) -> str:
    settings = get_settings()
    claims = {
        "sub": principal.user_id,
        "type": "refresh",
    }
    return _create_token(claims, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        msg = "Invalid or expired token."
        raise ValueError(msg) from exc
    return payload
