from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import ElevationCreate, ElevationRead, ElevationUpdate, Orientation
from app.services.elevation_service import ElevationService

router = APIRouter(tags=["elevations"])


def get_service(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ElevationService:
    return ElevationService(session, user)


@router.post(
    "/projects/{project_id}/elevations",
    response_model=ElevationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_elevation(
    project_id: int,
    data: ElevationCreate,
    service: ElevationService = Depends(get_service),
):
    return service.create(project_id, data)


@router.get("/projects/{project_id}/elevations", response_model=list[ElevationRead])
def list_elevations(
    project_id: int,
    orientation: Orientation | None = None,
    service: ElevationService = Depends(get_service),
):
    return service.list(project_id, orientation=orientation)


@router.get("/elevations/{elevation_id}", response_model=ElevationRead)
def get_elevation(elevation_id: int, service: ElevationService = Depends(get_service)):
    return service.get(elevation_id)


@router.patch("/elevations/{elevation_id}", response_model=ElevationRead)
def update_elevation(
    elevation_id: int,
    data: ElevationUpdate,
    service: ElevationService = Depends(get_service),
):
    return service.update(elevation_id, data)


@router.delete("/elevations/{elevation_id}", status_code=204)
def delete_elevation(elevation_id: int, service: ElevationService = Depends(get_service)):
    service.delete(elevation_id)
    return Response(status_code=204)
