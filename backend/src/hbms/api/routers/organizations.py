from fastapi import APIRouter, Depends

from hbms.api.dependencies import get_current_principal
from hbms.domain.schemas import (
    AuthenticatedPrincipal,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from hbms.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead)
async def create_organization(
    payload: OrganizationCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> OrganizationRead:
    return await OrganizationService.create(principal, payload)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> list[OrganizationRead]:
    return await OrganizationService.list_organizations(principal)


@router.patch("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> OrganizationRead:
    return await OrganizationService.update(principal, organization_id, payload)
