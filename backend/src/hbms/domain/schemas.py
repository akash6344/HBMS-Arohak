from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, ValidationInfo, field_validator

from hbms.domain.enums import (
    BookingStatus,
    CancellationRequestStatus,
    EntityStatus,
    Role,
    RoomAvailabilityStatus,
)


def _validate_object_id(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and ObjectId.is_valid(value):
        return value
    msg = "Invalid ObjectId."
    raise ValueError(msg)


def _coerce_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


ObjectIdStr = Annotated[str, BeforeValidator(_validate_object_id)]
DecimalAmount = Annotated[Decimal, BeforeValidator(_coerce_decimal)]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class TimestampModel(ApiModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserCreate(ApiModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(TimestampModel):
    id: ObjectIdStr = Field(alias="_id")
    name: str
    email: EmailStr
    role: Role


class TokenResponse(ApiModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthenticatedPrincipal(ApiModel):
    user_id: ObjectIdStr
    role: Role
    organization_ids: list[ObjectIdStr] = Field(default_factory=list)
    hotel_ids: list[ObjectIdStr] = Field(default_factory=list)


class OrganizationCreate(ApiModel):
    name: str = Field(min_length=2, max_length=160)


class OrganizationUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    status: EntityStatus | None = None


class OrganizationRead(TimestampModel):
    id: ObjectIdStr = Field(alias="_id")
    name: str
    status: EntityStatus


class HotelCreate(ApiModel):
    name: str = Field(min_length=2, max_length=160)
    address: str = Field(min_length=2, max_length=255)
    city: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=2, max_length=2000)
    contact_number: str = Field(min_length=5, max_length=32)
    email: EmailStr
    timezone: str = Field(min_length=2, max_length=64)


class HotelUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    address: str | None = Field(default=None, min_length=2, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, min_length=2, max_length=2000)
    contact_number: str | None = Field(default=None, min_length=5, max_length=32)
    email: EmailStr | None = None
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    status: EntityStatus | None = None


class HotelRead(TimestampModel):
    id: ObjectIdStr = Field(alias="_id")
    organization_id: ObjectIdStr
    name: str
    address: str
    city: str
    description: str
    contact_number: str
    email: EmailStr
    timezone: str
    status: EntityStatus


class RoomCreate(ApiModel):
    room_number: str = Field(min_length=1, max_length=32)
    room_type: str = Field(min_length=2, max_length=64)
    capacity: int = Field(ge=1, le=20)
    price_per_night: DecimalAmount = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    availability_status: RoomAvailabilityStatus = RoomAvailabilityStatus.AVAILABLE
    description: str = Field(min_length=2, max_length=2000)
    amenities: list[str] = Field(default_factory=list)

    @field_validator("amenities")
    @classmethod
    def normalize_amenities(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        return sorted(set(cleaned))

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class RoomUpdate(ApiModel):
    room_number: str | None = Field(default=None, min_length=1, max_length=32)
    room_type: str | None = Field(default=None, min_length=2, max_length=64)
    capacity: int | None = Field(default=None, ge=1, le=20)
    price_per_night: DecimalAmount | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    availability_status: RoomAvailabilityStatus | None = None
    description: str | None = Field(default=None, min_length=2, max_length=2000)
    amenities: list[str] | None = None

    @field_validator("amenities")
    @classmethod
    def normalize_amenities(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if item.strip()]
        return sorted(set(cleaned))

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class RoomRead(TimestampModel):
    id: ObjectIdStr = Field(alias="_id")
    organization_id: ObjectIdStr
    hotel_id: ObjectIdStr
    hotel_name: str | None = None
    hotel_city: str | None = None
    room_number: str
    room_type: str
    capacity: int
    price_per_night: DecimalAmount
    currency: str
    availability_status: RoomAvailabilityStatus
    is_active: bool
    description: str
    amenities: list[str]


class BookingCreate(ApiModel):
    room_id: ObjectIdStr
    check_in_date: date
    check_out_date: date
    guest_count: int = Field(ge=1, le=20)

    @field_validator("check_out_date")
    @classmethod
    def validate_dates(cls, check_out_date: date, info: ValidationInfo) -> date:
        check_in_date = info.data.get("check_in_date")
        if isinstance(check_in_date, date) and check_out_date <= check_in_date:
            msg = "check_out_date must be after check_in_date."
            raise ValueError(msg)
        return check_out_date


class BookingRead(TimestampModel):
    id: ObjectIdStr = Field(alias="_id")
    booking_ref: str
    organization_id: ObjectIdStr
    hotel_id: ObjectIdStr
    room_id: ObjectIdStr
    customer_id: ObjectIdStr
    check_in_date: date
    check_out_date: date
    guest_count: int
    booking_date: datetime
    nightly_rate_snapshot: DecimalAmount
    currency: str
    total_amount: DecimalAmount
    status: BookingStatus
    cancellation_deadline_at: datetime


class CancellationRequestCreate(ApiModel):
    reason: str = Field(min_length=3, max_length=1000)


class CancellationRequestRead(TimestampModel):
    id: ObjectIdStr = Field(alias="_id")
    booking_id: ObjectIdStr
    organization_id: ObjectIdStr
    hotel_id: ObjectIdStr
    requested_by: ObjectIdStr
    reason: str
    status: CancellationRequestStatus
    reviewed_by: ObjectIdStr | None = None
    reviewed_at: datetime | None = None


class CreateOrgAdminRequest(ApiModel):
    organization_id: ObjectIdStr
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class CreateReceptionistRequest(ApiModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    hotel_ids: list[ObjectIdStr] = Field(min_length=1)


class AssignReceptionistHotelsRequest(ApiModel):
    hotel_ids: list[ObjectIdStr] = Field(min_length=1)


class RefreshTokenRequest(ApiModel):
    refresh_token: str = Field(min_length=20)
