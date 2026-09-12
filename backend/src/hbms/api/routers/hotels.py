from fastapi import APIRouter, Depends

from hbms.api.dependencies import get_current_principal
from hbms.domain.schemas import AuthenticatedPrincipal, HotelCreate, HotelRead, HotelUpdate
from hbms.services.hotel_service import HotelService

router = APIRouter(tags=["hotels"])


@router.post("/organizations/{organization_id}/hotels", response_model=HotelRead)
async def create_hotel(
    organization_id: str,
    payload: HotelCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> HotelRead:
    return await HotelService.create(principal, organization_id, payload)


@router.get("/organizations/{organization_id}/hotels", response_model=list[HotelRead])
async def list_hotels(
    organization_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> list[HotelRead]:
    return await HotelService.list_by_organization(principal, organization_id)


@router.patch("/hotels/{hotel_id}", response_model=HotelRead)
async def update_hotel(
    hotel_id: str,
    payload: HotelUpdate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> HotelRead:
    return await HotelService.update(principal, hotel_id, payload)
