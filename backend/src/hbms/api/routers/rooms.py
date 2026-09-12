from fastapi import APIRouter, Depends

from hbms.api.dependencies import get_current_principal
from hbms.domain.schemas import AuthenticatedPrincipal, RoomCreate, RoomRead, RoomUpdate
from hbms.services.room_service import RoomService

router = APIRouter(prefix="/hotels/{hotel_id}/rooms", tags=["rooms"])


@router.post("", response_model=RoomRead)
async def create_room(
    hotel_id: str,
    payload: RoomCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> RoomRead:
    return await RoomService.create(principal, hotel_id, payload)


@router.get("", response_model=list[RoomRead])
async def list_rooms(
    hotel_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> list[RoomRead]:
    return await RoomService.list_by_hotel(principal, hotel_id)


@router.patch("/{room_id}", response_model=RoomRead)
async def update_room(
    hotel_id: str,
    room_id: str,
    payload: RoomUpdate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> RoomRead:
    return await RoomService.update(principal, hotel_id, room_id, payload)


@router.post("/{room_id}/deactivate", response_model=RoomRead)
async def deactivate_room(
    hotel_id: str,
    room_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> RoomRead:
    return await RoomService.deactivate(principal, hotel_id, room_id)
