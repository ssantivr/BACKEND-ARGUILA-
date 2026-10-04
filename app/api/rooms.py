from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import RoomCreate, RoomRead, RoomUpdate
from app.services.room_service import RoomService

router = APIRouter(tags=["rooms"])


def get_service(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RoomService:
    return RoomService(session, user)


@router.post(
    "/projects/{project_id}/rooms",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
)
def create_room(
    project_id: int,
    data: RoomCreate,
    service: RoomService = Depends(get_service),
):
    return service.create(project_id, data)


@router.get("/projects/{project_id}/rooms", response_model=list[RoomRead])
def list_rooms(project_id: int, service: RoomService = Depends(get_service)):
    return service.list(project_id)


@router.get("/rooms/{room_id}", response_model=RoomRead)
def get_room(room_id: int, service: RoomService = Depends(get_service)):
    return service.get(room_id)


@router.patch("/rooms/{room_id}", response_model=RoomRead)
def update_room(
    room_id: int,
    data: RoomUpdate,
    service: RoomService = Depends(get_service),
):
    return service.update(room_id, data)


@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, service: RoomService = Depends(get_service)):
    service.delete(room_id)
    return Response(status_code=204)
