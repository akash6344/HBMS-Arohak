from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from hbms.auth.passwords import hash_password, verify_password
from hbms.auth.tokens import create_access_token, create_refresh_token, decode_token
from hbms.core.config import get_settings
from hbms.domain.schemas import (
    AuthenticatedPrincipal,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from hbms.repositories.refresh_token_repository import RefreshTokenRepository
from hbms.repositories.user_repository import UserAlreadyExistsError, UserRepository


class AuthService:
    @staticmethod
    def _to_principal(user_document: dict) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            user_id=str(user_document["_id"]),
            role=user_document["role"],
            organization_ids=[
                str(organization_id) for organization_id in user_document.get("organization_ids", [])
            ],
            hotel_ids=[str(hotel_id) for hotel_id in user_document.get("hotel_ids", [])],
        )

    @staticmethod
    async def _issue_tokens(user_document: dict) -> TokenResponse:
        principal = AuthService._to_principal(user_document)
        access_token = create_access_token(principal)
        refresh_token = create_refresh_token(principal)
        settings = get_settings()
        await RefreshTokenRepository.create(
            user_id=principal.user_id,
            token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    async def register_customer(payload: UserCreate) -> UserRead:
        password_hash = hash_password(payload.password)
        try:
            created_user = await UserRepository.create_customer(payload, password_hash)
        except UserAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists.",
            ) from exc
        return UserRead.model_validate(created_user)

    @staticmethod
    async def login(email: str, password: str) -> TokenResponse:
        user_document = await UserRepository.get_by_email(email)
        invalid_credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
        if user_document is None:
            raise invalid_credentials_error
        if not verify_password(password, str(user_document["password_hash"])):
            raise invalid_credentials_error
        return await AuthService._issue_tokens(user_document)

    @staticmethod
    async def refresh(payload: RefreshTokenRequest) -> TokenResponse:
        try:
            token_payload = decode_token(payload.refresh_token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            ) from exc

        if token_payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type.",
            )

        stored = await RefreshTokenRepository.get_active(payload.refresh_token)
        if stored is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is revoked or expired.",
            )

        user_id = token_payload.get("sub")
        if not isinstance(user_id, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token subject.",
            )

        user_document = await UserRepository.get_by_id(user_id)
        if user_document is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
            )

        await RefreshTokenRepository.revoke(payload.refresh_token)
        return await AuthService._issue_tokens(user_document)

    @staticmethod
    async def logout(payload: RefreshTokenRequest) -> dict[str, str]:
        await RefreshTokenRepository.revoke(payload.refresh_token)
        return {"status": "logged_out"}
