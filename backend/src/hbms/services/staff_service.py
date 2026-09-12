from fastapi import HTTPException, status

from hbms.auth.passwords import hash_password
from hbms.domain.enums import Role
from hbms.domain.schemas import (
    AssignReceptionistHotelsRequest,
    AuthenticatedPrincipal,
    CreateOrgAdminRequest,
    CreateReceptionistRequest,
    UserRead,
)
from hbms.policy.authorization import ensure_organization_access, require_role
from hbms.repositories.hotel_repository import HotelRepository
from hbms.repositories.organization_repository import OrganizationRepository
from hbms.repositories.user_repository import UserAlreadyExistsError, UserRepository


class StaffService:
    @staticmethod
    async def create_org_admin(
        principal: AuthenticatedPrincipal,
        payload: CreateOrgAdminRequest,
    ) -> UserRead:
        require_role(principal, {Role.PRODUCT_ADMIN})
        organization = await OrganizationRepository.get_by_id(payload.organization_id)
        if organization is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

        try:
            created = await UserRepository.create_staff_user(
                name=payload.name,
                email=str(payload.email),
                password_hash=hash_password(payload.password),
                role=Role.ORG_ADMIN,
                organization_ids=[payload.organization_id],
                hotel_ids=[],
            )
        except UserAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists.",
            ) from exc
        return UserRead.model_validate(created)

    @staticmethod
    async def create_receptionist(
        principal: AuthenticatedPrincipal,
        payload: CreateReceptionistRequest,
    ) -> UserRead:
        require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN})
        if not principal.organization_ids and principal.role == Role.ORG_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization scope is missing.",
            )

        organization_id = (
            principal.organization_ids[0]
            if principal.role == Role.ORG_ADMIN
            else None
        )
        hotel_ids: list[str] = []
        for hotel_id in payload.hotel_ids:
            hotel = await HotelRepository.get_by_id(hotel_id)
            if hotel is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
            hotel_organization_id = str(hotel["organization_id"])
            if principal.role == Role.ORG_ADMIN:
                ensure_organization_access(principal, hotel_organization_id)
                if organization_id is None:
                    organization_id = hotel_organization_id
                elif organization_id != hotel_organization_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="All hotels must belong to the same organization.",
                    )
            hotel_ids.append(hotel_id)
            organization_id = organization_id or hotel_organization_id

        if organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to resolve organization for receptionist.",
            )

        try:
            created = await UserRepository.create_staff_user(
                name=payload.name,
                email=str(payload.email),
                password_hash=hash_password(payload.password),
                role=Role.RECEPTIONIST,
                organization_ids=[organization_id],
                hotel_ids=hotel_ids,
            )
        except UserAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists.",
            ) from exc
        return UserRead.model_validate(created)

    @staticmethod
    async def assign_receptionist_hotels(
        principal: AuthenticatedPrincipal,
        receptionist_id: str,
        payload: AssignReceptionistHotelsRequest,
    ) -> UserRead:
        require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN})
        receptionist = await UserRepository.get_by_id(receptionist_id)
        if receptionist is None or receptionist.get("role") != Role.RECEPTIONIST.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receptionist not found.")

        receptionist_org_ids = {
            str(organization_id) for organization_id in receptionist.get("organization_ids", [])
        }
        for hotel_id in payload.hotel_ids:
            hotel = await HotelRepository.get_by_id(hotel_id)
            if hotel is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")
            hotel_organization_id = str(hotel["organization_id"])
            if hotel_organization_id not in receptionist_org_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Hotel does not belong to the receptionist's organization.",
                )
            if principal.role == Role.ORG_ADMIN:
                ensure_organization_access(principal, hotel_organization_id)

        updated = await UserRepository.assign_hotels(receptionist_id, payload.hotel_ids)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receptionist not found.")
        return UserRead.model_validate(updated)
