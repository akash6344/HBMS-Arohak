from datetime import date

from fastapi import APIRouter, Depends, Header, Query

from hbms.api.dependencies import get_current_principal
from hbms.domain.enums import BookingStatus, CancellationRequestStatus
from hbms.domain.schemas import (
    AuthenticatedPrincipal,
    BookingCreate,
    BookingRead,
    CancellationRequestCreate,
    CancellationRequestRead,
    RoomRead,
)
from hbms.services.booking_service import BookingService

router = APIRouter(tags=["bookings"])


@router.get("/search/rooms", response_model=list[RoomRead])
async def search_rooms(
    check_in: date = Query(...),
    check_out: date = Query(...),
    guests: int = Query(..., ge=1, le=20),
    city: str | None = Query(default=None),
    organization_id: str | None = Query(default=None),
    hotel_id: str | None = Query(default=None),
    _: AuthenticatedPrincipal = Depends(get_current_principal),
) -> list[RoomRead]:
    return await BookingService.search_rooms(
        check_in_date=check_in,
        check_out_date=check_out,
        guest_count=guests,
        city=city,
        organization_id=organization_id,
        hotel_id=hotel_id,
    )


@router.post("/bookings", response_model=BookingRead)
async def create_booking(
    payload: BookingCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> BookingRead:
    return await BookingService.create_booking(
        principal,
        payload,
        idempotency_key=idempotency_key,
    )


@router.get("/bookings", response_model=list[BookingRead])
async def list_my_bookings(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> list[BookingRead]:
    return await BookingService.list_my_bookings(principal)


@router.get("/bookings/cancellation-requests", response_model=list[CancellationRequestRead])
async def list_my_cancellation_requests(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> list[CancellationRequestRead]:
    return await BookingService.list_my_cancellation_requests(principal)


@router.get("/bookings/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> BookingRead:
    return await BookingService.get_booking(principal, booking_id)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)
async def cancel_booking(
    booking_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> BookingRead:
    return await BookingService.cancel_booking(principal, booking_id)


@router.post(
    "/bookings/{booking_id}/cancellation-requests",
    response_model=CancellationRequestRead,
)
async def create_cancellation_request(
    booking_id: str,
    payload: CancellationRequestCreate,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> CancellationRequestRead:
    return await BookingService.create_cancellation_request(principal, booking_id, payload)


@router.get("/staff/bookings", response_model=list[BookingRead])
async def list_staff_bookings(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    status_value: BookingStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    hotel_id: str | None = Query(default=None),
    room_id: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    booking_ref: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[BookingRead]:
    return await BookingService.list_staff_bookings(
        principal,
        status_value=status_value,
        date_from=date_from,
        date_to=date_to,
        hotel_id=hotel_id,
        room_id=room_id,
        customer_query=customer,
        booking_ref=booking_ref,
        skip=skip,
        limit=limit,
    )


@router.get("/staff/bookings/{booking_id}", response_model=BookingRead)
async def get_staff_booking(
    booking_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> BookingRead:
    return await BookingService.get_booking(principal, booking_id)


@router.get("/staff/cancellation-requests", response_model=list[CancellationRequestRead])
async def list_cancellation_requests(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    status_value: CancellationRequestStatus | None = Query(default=None, alias="status"),
) -> list[CancellationRequestRead]:
    return await BookingService.list_cancellation_requests(
        principal,
        status_value=status_value,
    )


@router.post(
    "/staff/cancellation-requests/{request_id}/approve",
    response_model=CancellationRequestRead,
)
async def approve_cancellation_request(
    request_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> CancellationRequestRead:
    return await BookingService.review_cancellation_request(
        principal,
        request_id,
        approve=True,
    )


@router.post(
    "/staff/cancellation-requests/{request_id}/reject",
    response_model=CancellationRequestRead,
)
async def reject_cancellation_request(
    request_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> CancellationRequestRead:
    return await BookingService.review_cancellation_request(
        principal,
        request_id,
        approve=False,
    )
