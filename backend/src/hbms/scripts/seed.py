"""Seed demo data for local/reviewer demos.

Run from backend/:
  python -m hbms.scripts.seed
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from hbms.auth.passwords import hash_password
from hbms.core.config import get_settings
from hbms.db.mongo import mongo_manager
from hbms.domain.enums import Role
from hbms.domain.schemas import HotelCreate, OrganizationCreate, RoomCreate, UserCreate
from hbms.repositories.hotel_repository import HotelRepository
from hbms.repositories.organization_repository import OrganizationRepository
from hbms.repositories.room_repository import RoomRepository
from hbms.repositories.user_repository import UserAlreadyExistsError, UserRepository


DEMO_PASSWORD = "Password123!"


async def _upsert_user(
    *,
    name: str,
    email: str,
    role: Role,
    organization_ids: list[str],
    hotel_ids: list[str],
) -> dict:
    existing = await UserRepository.get_by_email(email)
    if existing is not None:
        return existing
    if role == Role.CUSTOMER:
        return await UserRepository.create_customer(
            UserCreate(name=name, email=email, password=DEMO_PASSWORD),
            hash_password(DEMO_PASSWORD),
        )
    return await UserRepository.create_staff_user(
        name=name,
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        role=role,
        organization_ids=organization_ids,
        hotel_ids=hotel_ids,
    )


async def seed() -> None:
    settings = get_settings()
    await mongo_manager.connect()
    print(f"Seeding database `{settings.mongodb_database}`...")

    organizations = await OrganizationRepository.list_all()
    if organizations:
        organization = organizations[0]
        print(f"Using existing organization: {organization['name']}")
    else:
        organization = await OrganizationRepository.create(
            OrganizationCreate(name="Arohak Hospitality Group")
        )
        print(f"Created organization: {organization['name']}")

    organization_id = str(organization["_id"])
    hotels = await HotelRepository.list_by_organization(organization_id)
    if hotels:
        hotel = hotels[0]
        print(f"Using existing hotel: {hotel['name']}")
    else:
        hotel = await HotelRepository.create(
            organization_id,
            HotelCreate(
                name="Arohak Grand Mumbai",
                address="12 Marine Drive",
                city="Mumbai",
                description="Waterfront business hotel with modern amenities.",
                contact_number="+91-22-4000-1000",
                email="front.desk@arohakgrand.example",
                timezone="Asia/Kolkata",
            ),
        )
        print(f"Created hotel: {hotel['name']}")

    hotel_id = str(hotel["_id"])
    rooms = await RoomRepository.list_by_hotel(organization_id, hotel_id)
    if not rooms:
        for payload in (
            RoomCreate(
                room_number="101",
                room_type="Deluxe",
                capacity=2,
                price_per_night=Decimal("4500.00"),
                currency="INR",
                description="City-view deluxe room with king bed.",
                amenities=["WiFi", "AC", "TV"],
            ),
            RoomCreate(
                room_number="202",
                room_type="Suite",
                capacity=4,
                price_per_night=Decimal("8500.00"),
                currency="INR",
                description="Spacious suite with living area.",
                amenities=["WiFi", "AC", "TV", "Mini Bar"],
            ),
            RoomCreate(
                room_number="303",
                room_type="Standard",
                capacity=2,
                price_per_night=Decimal("3200.00"),
                currency="INR",
                description="Comfortable standard room for short stays.",
                amenities=["WiFi", "AC"],
            ),
        ):
            await RoomRepository.create(
                organization_id=organization_id,
                hotel_id=hotel_id,
                payload=payload,
            )
        print("Created sample rooms: 101, 202, 303")
    else:
        print(f"Using existing rooms: {len(rooms)}")

    product_admin = await _upsert_user(
        name="Product Admin",
        email="product.admin@hbms.example",
        role=Role.PRODUCT_ADMIN,
        organization_ids=[],
        hotel_ids=[],
    )
    org_admin = await _upsert_user(
        name="Org Admin",
        email="org.admin@hbms.example",
        role=Role.ORG_ADMIN,
        organization_ids=[organization_id],
        hotel_ids=[],
    )
    receptionist = await _upsert_user(
        name="Receptionist",
        email="receptionist@hbms.example",
        role=Role.RECEPTIONIST,
        organization_ids=[organization_id],
        hotel_ids=[hotel_id],
    )
    try:
        customer = await _upsert_user(
            name="Demo Customer",
            email="customer@hbms.example",
            role=Role.CUSTOMER,
            organization_ids=[],
            hotel_ids=[],
        )
    except UserAlreadyExistsError:
        customer = await UserRepository.get_by_email("customer@hbms.example")

    print("\nSeed complete. Demo credentials (password for all: Password123!):")
    print(f"- PRODUCT_ADMIN : product.admin@hbms.example  id={product_admin['_id']}")
    print(f"- ORG_ADMIN     : org.admin@hbms.example      id={org_admin['_id']}")
    print(f"- RECEPTIONIST  : receptionist@hbms.example   id={receptionist['_id']}")
    print(f"- CUSTOMER      : customer@hbms.example       id={customer['_id'] if customer else 'n/a'}")
    print(f"- organization  : {organization_id}")
    print(f"- hotel         : {hotel_id}")

    await mongo_manager.disconnect()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
