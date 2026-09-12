from fastapi import APIRouter, Depends

from hbms.api.dependencies import get_current_principal
from hbms.api.schemas.auth import LoginRequest
from hbms.domain.schemas import (
    AuthenticatedPrincipal,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from hbms.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead)
async def register(payload: UserCreate) -> UserRead:
    return await AuthService.register_customer(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    return await AuthService.login(email=str(payload.email), password=payload.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest) -> TokenResponse:
    return await AuthService.refresh(payload)


@router.post("/logout")
async def logout(payload: RefreshTokenRequest) -> dict[str, str]:
    return await AuthService.logout(payload)


@router.get("/me", response_model=AuthenticatedPrincipal)
async def me(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> AuthenticatedPrincipal:
    return principal
