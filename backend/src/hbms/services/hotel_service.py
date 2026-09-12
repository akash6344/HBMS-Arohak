from fastapi import HTTPException, status

from hbms.domain.enums import Role
from hbms.domain.schemas import AuthenticatedPrincipal, HotelCreate, HotelRead, HotelUpdate
from hbms.policy.authorization import (
    ensure_hotel_access,
    ensure_organization_access,
    require_role,
)
from hbms.repositories.hotel_repository import HotelRepository
from hbms.repositories.organization_repository import OrganizationRepository


class HotelService:
    @staticmethod
    async def get_scoped_hotel(
        principal: AuthenticatedPrincipal,
        hotel_id: str,
    ) -> dict:
        hotel = await HotelRepository.get_by_id(hotel_id)
        if hotel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")

        organization_id = str(hotel["organization_id"])
        if principal.role != Role.PRODUCT_ADMIN:
            if principal.role in {Role.ORG_ADMIN, Role.RECEPTIONIST}:
                ensure_organization_access(principal, organization_id)
            if principal.role == Role.RECEPTIONIST:
                ensure_hotel_access(principal, hotel_id)
        return hotel

    @staticmethod
    async def create(
        principal: AuthenticatedPrincipal,
        organization_id: str,
        payload: HotelCreate,
    ) -> HotelRead:
        require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN})
        ensure_organization_access(principal, organization_id)

        organization = await OrganizationRepository.get_by_id(organization_id)
        if organization is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

        created = await HotelRepository.create(organization_id, payload)
        return HotelRead.model_validate(created)

    @staticmethod
    async def list_by_organization(
        principal: AuthenticatedPrincipal,
        organization_id: str,
    ) -> list[HotelRead]:
        organization = await OrganizationRepository.get_by_id(organization_id)
        if organization is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

        if principal.role in {Role.PRODUCT_ADMIN, Role.CUSTOMER}:
            hotels = await HotelRepository.list_by_organization(organization_id)
            if principal.role == Role.CUSTOMER:
                hotels = [hotel for hotel in hotels if hotel.get("status") == "ACTIVE"]
            return [HotelRead.model_validate(hotel) for hotel in hotels]

        ensure_organization_access(principal, organization_id)
        hotels = await HotelRepository.list_by_organization(organization_id)
        if principal.role == Role.RECEPTIONIST:
            hotels = [hotel for hotel in hotels if str(hotel["_id"]) in principal.hotel_ids]
        return [HotelRead.model_validate(hotel) for hotel in hotels]

    @staticmethod
    async def update(
        principal: AuthenticatedPrincipal,
        hotel_id: str,
        payload: HotelUpdate,
    ) -> HotelRead:
        require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN})
        hotel = await HotelService.get_scoped_hotel(principal, hotel_id)
        ensure_organization_access(principal, str(hotel["organization_id"]))
        updated = await HotelRepository.update(hotel_id, payload)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
        return HotelRead.model_validate(updated)
