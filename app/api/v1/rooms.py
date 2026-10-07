from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require
from app.database import get_session
from app.dtos import RoomCategory, RoomSpatialRead, RoomSpatialUpdate
from app.models import User
from app.services.room_spatial_service import RoomSpatialService

router = APIRouter(prefix="/rooms", tags=["rooms"])


def reader(
    session: Session = Depends(get_session),
    user: User = Depends(require("rooms:read")),
) -> RoomSpatialService:
    return RoomSpatialService(session, user)


def writer(
    session: Session = Depends(get_session),
    user: User = Depends(require("rooms:write")),
) -> RoomSpatialService:
    return RoomSpatialService(session, user)


@router.get("", response_model=list[RoomSpatialRead])
def list_rooms(
    project_id: int,
    unit_id: int | None = None,
    category: RoomCategory | None = None,
    service: RoomSpatialService = Depends(reader),
):
    return service.list(project_id, unit_id, category)


@router.get("/{room_id}", response_model=RoomSpatialRead)
def get_room(room_id: int, service: RoomSpatialService = Depends(reader)):
    return service.get(room_id)


@router.patch("/{room_id}", response_model=RoomSpatialRead)
def update_room(
    room_id: int,
    data: RoomSpatialUpdate,
    service: RoomSpatialService = Depends(writer),
):
    return service.update(room_id, data)
