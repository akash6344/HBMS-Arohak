from fastapi import HTTPException, status

from hbms.domain.enums import Role
from hbms.domain.schemas import AuthenticatedPrincipal
from hbms.domain.tenant import TenantContext


def require_role(principal: AuthenticatedPrincipal, allowed_roles: set[Role]) -> None:
    if principal.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )


def to_tenant_context(principal: AuthenticatedPrincipal) -> TenantContext:
    return TenantContext(
        user_id=principal.user_id,
        role=principal.role,
        organization_ids=tuple(principal.organization_ids),
        hotel_ids=tuple(principal.hotel_ids),
    )


def ensure_organization_access(principal: AuthenticatedPrincipal, organization_id: str) -> None:
    if principal.role == Role.PRODUCT_ADMIN:
        return
    if principal.role in {Role.ORG_ADMIN, Role.RECEPTIONIST}:
        if organization_id not in principal.organization_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to perform this action.",
    )


def ensure_hotel_access(principal: AuthenticatedPrincipal, hotel_id: str) -> None:
    if principal.role == Role.PRODUCT_ADMIN:
        return
    if principal.role == Role.ORG_ADMIN:
        return
    if principal.role == Role.RECEPTIONIST:
        if hotel_id not in principal.hotel_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hotel not found.",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to perform this action.",
    )


def ensure_can_manage_rooms(principal: AuthenticatedPrincipal) -> None:
    require_role(
        principal,
        {Role.PRODUCT_ADMIN, Role.ORG_ADMIN, Role.RECEPTIONIST},
    )


def ensure_can_mutate_rooms(principal: AuthenticatedPrincipal) -> None:
    """Receptionists can manage availability/bookings, not create/delete room inventory."""
    require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN})
