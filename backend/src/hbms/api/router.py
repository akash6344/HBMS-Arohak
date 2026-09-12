from fastapi import APIRouter

from hbms.api.routers.ai import router as ai_router
from hbms.api.routers.auth import router as auth_router
from hbms.api.routers.bookings import router as bookings_router
from hbms.api.routers.health import router as health_router
from hbms.api.routers.hotels import router as hotels_router
from hbms.api.routers.organizations import router as organizations_router
from hbms.api.routers.rooms import router as rooms_router
from hbms.api.routers.staff import router as staff_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(organizations_router)
api_router.include_router(hotels_router)
api_router.include_router(rooms_router)
api_router.include_router(bookings_router)
api_router.include_router(staff_router)
api_router.include_router(ai_router)
