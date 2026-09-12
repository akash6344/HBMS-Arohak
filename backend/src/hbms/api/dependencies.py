from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hbms.auth.tokens import decode_token
from hbms.domain.enums import Role
from hbms.domain.schemas import AuthenticatedPrincipal

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthenticatedPrincipal:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    role_raw = payload.get("role")
    if not isinstance(role_raw, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token role is missing.",
        )

    try:
        role = Role(role_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token role is invalid.",
        ) from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is missing.",
        )

    organization_ids_raw = payload.get("organization_ids", [])
    hotel_ids_raw = payload.get("hotel_ids", [])
    organization_ids = organization_ids_raw if isinstance(organization_ids_raw, list) else []
    hotel_ids = hotel_ids_raw if isinstance(hotel_ids_raw, list) else []

    return AuthenticatedPrincipal(
        user_id=user_id,
        role=role,
        organization_ids=organization_ids,
        hotel_ids=hotel_ids,
    )
