from fastapi import APIRouter, Depends

from hbms.api.dependencies import get_current_principal
from hbms.domain.schemas import (
    AssignReceptionistHotelsRequest,
    AuthenticatedPrincipal,
    CreateOrgAdminRequest,
    CreateReceptionistRequest,
    UserRead,
)
from hbms.services.staff_service import StaffService

router = APIRouter(prefix="/staff", tags=["staff"])


@router.post("/org-admins", response_model=UserRead)
async def create_org_admin(
    payload: CreateOrgAdminRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> UserRead:
    return await StaffService.create_org_admin(principal, payload)


@router.post("/receptionists", response_model=UserRead)
async def create_receptionist(
    payload: CreateReceptionistRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> UserRead:
    return await StaffService.create_receptionist(principal, payload)


@router.post("/receptionists/{receptionist_id}/hotels", response_model=UserRead)
async def assign_receptionist_hotels(
    receptionist_id: str,
    payload: AssignReceptionistHotelsRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> UserRead:
    return await StaffService.assign_receptionist_hotels(principal, receptionist_id, payload)
