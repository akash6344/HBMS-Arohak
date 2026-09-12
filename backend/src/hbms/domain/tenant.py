from dataclasses import dataclass

from hbms.domain.enums import Role


@dataclass(frozen=True)
class TenantContext:
    user_id: str
    role: Role
    organization_ids: tuple[str, ...]
    hotel_ids: tuple[str, ...]
