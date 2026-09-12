from enum import StrEnum


class Role(StrEnum):
    PRODUCT_ADMIN = "PRODUCT_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    RECEPTIONIST = "RECEPTIONIST"
    CUSTOMER = "CUSTOMER"


class EntityStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RoomAvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    MAINTENANCE = "MAINTENANCE"


class BookingStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class CancellationRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
