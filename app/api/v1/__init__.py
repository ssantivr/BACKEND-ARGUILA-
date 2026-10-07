from fastapi import APIRouter

from app.api.v1 import access, interior_walkthrough, properties, rooms, spatial_data, units

API_PREFIX = "/api/v1"

router = APIRouter(prefix=API_PREFIX)

router.include_router(access.router)
router.include_router(properties.router)
router.include_router(units.router)
router.include_router(rooms.router)
router.include_router(spatial_data.router)
router.include_router(interior_walkthrough.router)
