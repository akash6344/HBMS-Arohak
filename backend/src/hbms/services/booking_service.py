from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status

from hbms.domain.enums import (
    BookingStatus,
    CancellationRequestStatus,
    EntityStatus,
    Role,
    RoomAvailabilityStatus,
)
from hbms.domain.schemas import (
    AuthenticatedPrincipal,
    BookingCreate,
    BookingRead,
    CancellationRequestCreate,
    CancellationRequestRead,
    RoomRead,
)
from hbms.policy.authorization import require_role
from hbms.repositories.booking_repository import BookingConflictError, BookingRepository
from hbms.repositories.cancellation_request_repository import (
    CancellationRequestConflictError,
    CancellationRequestRepository,
)
from hbms.repositories.hotel_repository import HotelRepository
from hbms.repositories.idempotency_repository import IdempotencyRepository
from hbms.repositories.room_repository import RoomRepository
from hbms.repositories.user_repository import UserRepository


class BookingService:
    @staticmethod
    def _normalize_booking_document(document: dict) -> dict:
        normalized = dict(document)
        if isinstance(normalized.get("check_in_date"), str):
            normalized["check_in_date"] = date.fromisoformat(normalized["check_in_date"])
        if isinstance(normalized.get("check_out_date"), str):
            normalized["check_out_date"] = date.fromisoformat(normalized["check_out_date"])
        if isinstance(normalized.get("nightly_rate_snapshot"), str):
            normalized["nightly_rate_snapshot"] = Decimal(normalized["nightly_rate_snapshot"])
        if isinstance(normalized.get("total_amount"), str):
            normalized["total_amount"] = Decimal(normalized["total_amount"])
        if isinstance(normalized.get("price_per_night"), str):
            normalized["price_per_night"] = Decimal(normalized["price_per_night"])
        return normalized

    @staticmethod
    def _build_booking_ref() -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"BK-{stamp}"

    @staticmethod
    async def search_rooms(
        *,
        check_in_date: date,
        check_out_date: date,
        guest_count: int,
        city: str | None = None,
        organization_id: str | None = None,
        hotel_id: str | None = None,
    ) -> list[RoomRead]:
        if check_out_date <= check_in_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="check_out_date must be after check_in_date.",
            )
        if check_in_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="check_in_date cannot be in the past.",
            )

        hotels = await HotelRepository.list_active(city=city, organization_id=organization_id)
        if hotel_id:
            hotels = [hotel for hotel in hotels if str(hotel["_id"]) == hotel_id]
        hotel_by_id = {str(hotel["_id"]): hotel for hotel in hotels}
        hotel_ids = [hotel["_id"] for hotel in hotels]
        rooms = await RoomRepository.list_search_candidates(
            guest_count=guest_count,
            hotel_ids=hotel_ids,
        )
        conflicting = await BookingRepository.find_conflicting_room_ids(
            room_ids=[room["_id"] for room in rooms],
            check_in_date=check_in_date,
            check_out_date=check_out_date,
        )
        available: list[dict] = []
        for room in rooms:
            if str(room["_id"]) in conflicting:
                continue
            normalized = BookingService._normalize_booking_document(room)
            hotel = hotel_by_id.get(str(normalized["hotel_id"]))
            if hotel is not None:
                normalized["hotel_name"] = hotel.get("name")
                normalized["hotel_city"] = hotel.get("city")
            available.append(normalized)
        return [RoomRead.model_validate(room) for room in available]

    @staticmethod
    async def create_booking(
        principal: AuthenticatedPrincipal,
        payload: BookingCreate,
        *,
        idempotency_key: str | None = None,
    ) -> BookingRead:
        require_role(principal, {Role.CUSTOMER})

        endpoint = "POST /bookings"
        if idempotency_key:
            existing = await IdempotencyRepository.get(
                principal.user_id,
                endpoint,
                idempotency_key,
            )
            if existing is not None:
                return BookingRead.model_validate(existing["response_body"])

        if payload.check_in_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="check_in_date cannot be in the past.",
            )

        room = await RoomRepository.get_by_id(payload.room_id)
        if room is None or room.get("is_active") is not True:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
        if room.get("availability_status") != RoomAvailabilityStatus.AVAILABLE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Room is not available for booking.",
            )
        if int(room["capacity"]) < payload.guest_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guest count exceeds room capacity.",
            )

        hotel = await HotelRepository.get_by_id(str(room["hotel_id"]))
        if hotel is None or hotel.get("status") != EntityStatus.ACTIVE.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found.")

        try:
            created = await BookingRepository.create_with_day_locks(
                organization_id=str(room["organization_id"]),
                hotel_id=str(room["hotel_id"]),
                room_id=str(room["_id"]),
                customer_id=principal.user_id,
                check_in_date=payload.check_in_date,
                check_out_date=payload.check_out_date,
                guest_count=payload.guest_count,
                nightly_rate=Decimal(str(room["price_per_night"])),
                currency=str(room["currency"]),
                hotel_timezone=str(hotel["timezone"]),
                booking_ref=BookingService._build_booking_ref(),
            )
        except BookingConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Room is already booked for overlapping dates.",
            ) from exc

        booking = BookingRead.model_validate(BookingService._normalize_booking_document(created))
        if idempotency_key:
            await IdempotencyRepository.save(
                customer_id=principal.user_id,
                endpoint=endpoint,
                idempotency_key=idempotency_key,
                response_body=booking.model_dump(by_alias=True, mode="json"),
            )
        return booking

    @staticmethod
    async def list_my_bookings(principal: AuthenticatedPrincipal) -> list[BookingRead]:
        require_role(principal, {Role.CUSTOMER})
        documents = await BookingRepository.list_for_customer(principal.user_id)
        return [
            BookingRead.model_validate(BookingService._normalize_booking_document(document))
            for document in documents
        ]

    @staticmethod
    async def get_booking(
        principal: AuthenticatedPrincipal,
        booking_id: str,
    ) -> BookingRead:
        booking = await BookingRepository.get_by_id(booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        if principal.role == Role.CUSTOMER and str(booking["customer_id"]) != principal.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        if principal.role in {Role.ORG_ADMIN, Role.RECEPTIONIST}:
            organization_id = str(booking["organization_id"])
            hotel_id = str(booking["hotel_id"])
            if organization_id not in principal.organization_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
            if principal.role == Role.RECEPTIONIST and hotel_id not in principal.hotel_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        return BookingRead.model_validate(BookingService._normalize_booking_document(booking))

    @staticmethod
    async def cancel_booking(
        principal: AuthenticatedPrincipal,
        booking_id: str,
    ) -> BookingRead:
        booking = await BookingService.get_booking(principal, booking_id)
        if booking.status != BookingStatus.CONFIRMED:
            return booking

        if principal.role == Role.CUSTOMER:
            deadline = booking.cancellation_deadline_at
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
            if datetime.now(UTC) > deadline:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Direct cancellation window has closed. Submit a cancellation request.",
                )

        cancelled = await BookingRepository.cancel(booking_id)
        if cancelled is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        return BookingRead.model_validate(BookingService._normalize_booking_document(cancelled))

    @staticmethod
    async def create_cancellation_request(
        principal: AuthenticatedPrincipal,
        booking_id: str,
        payload: CancellationRequestCreate,
    ) -> CancellationRequestRead:
        require_role(principal, {Role.CUSTOMER})
        booking = await BookingService.get_booking(principal, booking_id)
        if booking.status != BookingStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only confirmed bookings can request cancellation.",
            )

        deadline = booking.cancellation_deadline_at
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        if datetime.now(UTC) <= deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direct cancellation is still available. Cancel the booking instead.",
            )

        existing = await CancellationRequestRepository.get_pending_for_booking(booking_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A cancellation request is already pending for this booking.",
            )

        try:
            created = await CancellationRequestRepository.create(
                booking_id=booking_id,
                organization_id=booking.organization_id,
                hotel_id=booking.hotel_id,
                requested_by=principal.user_id,
                reason=payload.reason,
            )
        except CancellationRequestConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A cancellation request is already pending for this booking.",
            ) from exc
        return CancellationRequestRead.model_validate(created)

    @staticmethod
    async def list_my_cancellation_requests(
        principal: AuthenticatedPrincipal,
    ) -> list[CancellationRequestRead]:
        require_role(principal, {Role.CUSTOMER})
        documents = await CancellationRequestRepository.list_for_requester(
            principal.user_id,
            status_value=CancellationRequestStatus.PENDING,
        )
        return [CancellationRequestRead.model_validate(document) for document in documents]

    @staticmethod
    async def list_staff_bookings(
        principal: AuthenticatedPrincipal,
        *,
        status_value: BookingStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        hotel_id: str | None = None,
        room_id: str | None = None,
        customer_query: str | None = None,
        booking_ref: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[BookingRead]:
        require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN, Role.RECEPTIONIST})

        organization_ids: list[str] | None = None
        hotel_ids: list[str] | None = None
        if principal.role == Role.ORG_ADMIN:
            organization_ids = list(principal.organization_ids)
        elif principal.role == Role.RECEPTIONIST:
            organization_ids = list(principal.organization_ids)
            hotel_ids = list(principal.hotel_ids)

        customer_ids = None
        if customer_query:
            customer_ids = await UserRepository.find_ids_by_email_or_name(customer_query)
            if not customer_ids:
                return []

        documents = await BookingRepository.list_for_staff(
            organization_ids=organization_ids,
            hotel_ids=hotel_ids,
            status_value=status_value,
            date_from=date_from,
            date_to=date_to,
            hotel_id=hotel_id,
            room_id=room_id,
            customer_ids=customer_ids,
            booking_ref=booking_ref,
            skip=skip,
            limit=limit,
        )
        return [
            BookingRead.model_validate(BookingService._normalize_booking_document(document))
            for document in documents
        ]

    @staticmethod
    async def list_cancellation_requests(
        principal: AuthenticatedPrincipal,
        *,
        status_value: CancellationRequestStatus | None = None,
    ) -> list[CancellationRequestRead]:
        require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN, Role.RECEPTIONIST})
        organization_ids: list[str] | None = None
        hotel_ids: list[str] | None = None
        if principal.role == Role.ORG_ADMIN:
            organization_ids = list(principal.organization_ids)
        elif principal.role == Role.RECEPTIONIST:
            organization_ids = list(principal.organization_ids)
            hotel_ids = list(principal.hotel_ids)

        documents = await CancellationRequestRepository.list_for_scope(
            organization_ids=organization_ids,
            hotel_ids=hotel_ids,
            status_value=status_value,
        )
        return [CancellationRequestRead.model_validate(document) for document in documents]

    @staticmethod
    async def review_cancellation_request(
        principal: AuthenticatedPrincipal,
        request_id: str,
        *,
        approve: bool,
    ) -> CancellationRequestRead:
        require_role(principal, {Role.PRODUCT_ADMIN, Role.ORG_ADMIN, Role.RECEPTIONIST})
        request_document = await CancellationRequestRepository.get_by_id(request_id)
        if request_document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cancellation request not found.",
            )

        organization_id = str(request_document["organization_id"])
        hotel_id = str(request_document["hotel_id"])
        if principal.role == Role.ORG_ADMIN and organization_id not in principal.organization_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cancellation request not found.",
            )
        if principal.role == Role.RECEPTIONIST and (
            organization_id not in principal.organization_ids or hotel_id not in principal.hotel_ids
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cancellation request not found.",
            )

        status_value = (
            CancellationRequestStatus.APPROVED if approve else CancellationRequestStatus.REJECTED
        )
        updated = await CancellationRequestRepository.mark_reviewed(
            request_id,
            status_value=status_value,
            reviewed_by=principal.user_id,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cancellation request is no longer pending.",
            )

        if approve:
            await BookingRepository.cancel(str(updated["booking_id"]))

        return CancellationRequestRead.model_validate(updated)
