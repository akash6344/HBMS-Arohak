from fastapi import HTTPException, status

from hbms.domain.enums import Role
from hbms.domain.schemas import (
    AuthenticatedPrincipal,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from hbms.policy.authorization import ensure_organization_access, require_role
from hbms.repositories.organization_repository import OrganizationRepository


class OrganizationService:
    @staticmethod
    async def create(
        principal: AuthenticatedPrincipal,
        payload: OrganizationCreate,
    ) -> OrganizationRead:
        require_role(principal, {Role.PRODUCT_ADMIN})
        created = await OrganizationRepository.create(payload)
        return OrganizationRead.model_validate(created)

    @staticmethod
    async def list_organizations(principal: AuthenticatedPrincipal) -> list[OrganizationRead]:
        if principal.role == Role.PRODUCT_ADMIN:
            documents = await OrganizationRepository.list_all()
            return [OrganizationRead.model_validate(document) for document in documents]

        if principal.role in {Role.ORG_ADMIN, Role.RECEPTIONIST}:
            documents = []
            for organization_id in principal.organization_ids:
                document = await OrganizationRepository.get_by_id(organization_id)
                if document is not None:
                    documents.append(document)
            return [OrganizationRead.model_validate(document) for document in documents]

        # Customers browse active organizations.
        documents = await OrganizationRepository.list_all()
        return [
            OrganizationRead.model_validate(document)
            for document in documents
            if document.get("status") == "ACTIVE"
        ]

    @staticmethod
    async def update(
        principal: AuthenticatedPrincipal,
        organization_id: str,
        payload: OrganizationUpdate,
    ) -> OrganizationRead:
        require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN})
        ensure_organization_access(principal, organization_id)
        updated = await OrganizationRepository.update(organization_id, payload)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
        return OrganizationRead.model_validate(updated)
