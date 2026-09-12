from fastapi import HTTPException, status

from hbms.domain.enums import Role
from hbms.domain.schemas import AuthenticatedPrincipal, RoomCreate, RoomRead, RoomUpdate
from hbms.policy.authorization import (
    ensure_can_manage_rooms,
    ensure_can_mutate_rooms,
    ensure_hotel_access,
    ensure_organization_access,
)
from hbms.repositories.hotel_repository import HotelRepository
from hbms.repositories.room_repository import RoomNumberConflictError, RoomRepository
from hbms.services.hotel_service import HotelService


class RoomService:
    @staticmethod
    async def create(
        principal: AuthenticatedPrincipal,
        hotel_id: str,
        payload: RoomCreate,
    ) -> RoomRead:
        ensure_can_mutate_rooms(principal)
        hotel = await HotelService.get_scoped_hotel(principal, hotel_id)
        organization_id = str(hotel["organization_id"])
        ensure_organization_access(principal, organization_id)

        try:
            created = await RoomRepository.create(
                organization_id=organization_id,
                hotel_id=hotel_id,
                payload=payload,
            )
        except RoomNumberConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Room number already exists for this hotel.",
            ) from exc
        return RoomRead.model_validate(created)

    @staticmethod
    async def list_by_hotel(
        principal: AuthenticatedPrincipal,
        hotel_id: str,
    ) -> list[RoomRead]:
        hotel = await HotelRepository.get_by_id(hotel_id)
        if hotel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")

        organization_id = str(hotel["organization_id"])
        if principal.role == Role.CUSTOMER:
            if hotel.get("status") != "ACTIVE":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
            rooms = await RoomRepository.list_by_hotel(organization_id, hotel_id)
            rooms = [room for room in rooms if room.get("is_active") is True]
            return [RoomRead.model_validate(room) for room in rooms]

        ensure_can_manage_rooms(principal)
        if principal.role != Role.PRODUCT_ADMIN:
            ensure_organization_access(principal, organization_id)
            if principal.role == Role.RECEPTIONIST:
                ensure_hotel_access(principal, hotel_id)

        rooms = await RoomRepository.list_by_hotel(organization_id, hotel_id)
        return [RoomRead.model_validate(room) for room in rooms]

    @staticmethod
    async def update(
        principal: AuthenticatedPrincipal,
        hotel_id: str,
        room_id: str,
        payload: RoomUpdate,
    ) -> RoomRead:
        ensure_can_manage_rooms(principal)
        hotel = await HotelService.get_scoped_hotel(principal, hotel_id)
        organization_id = str(hotel["organization_id"])
        ensure_organization_access(principal, organization_id)
        if principal.role == Role.RECEPTIONIST:
            ensure_hotel_access(principal, hotel_id)
            # Receptionists can update availability/description, not structural fields.
            restricted = {"room_number", "room_type", "capacity", "price_per_night", "currency"}
            if any(getattr(payload, field) is not None for field in restricted):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Receptionists cannot modify structural room fields.",
                )

        try:
            updated = await RoomRepository.update(
                room_id,
                organization_id=organization_id,
                hotel_id=hotel_id,
                payload=payload,
            )
        except RoomNumberConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Room number already exists for this hotel.",
            ) from exc

        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
        return RoomRead.model_validate(updated)

    @staticmethod
    async def deactivate(
        principal: AuthenticatedPrincipal,
        hotel_id: str,
        room_id: str,
    ) -> RoomRead:
        ensure_can_mutate_rooms(principal)
        hotel = await HotelService.get_scoped_hotel(principal, hotel_id)
        organization_id = str(hotel["organization_id"])
        ensure_organization_access(principal, organization_id)

        updated = await RoomRepository.deactivate(
            room_id,
            organization_id=organization_id,
            hotel_id=hotel_id,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
        return RoomRead.model_validate(updated)
