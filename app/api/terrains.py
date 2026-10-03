from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import TerrainCreate, TerrainRead, TerrainUpdate
from app.services.terrain_service import TerrainService

router = APIRouter(tags=["terrains"])


def get_service(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> TerrainService:
    return TerrainService(session, user)


@router.post(
    "/projects/{project_id}/terrains",
    response_model=TerrainRead,
    status_code=status.HTTP_201_CREATED,
)
def create_terrain(
    project_id: int,
    data: TerrainCreate,
    service: TerrainService = Depends(get_service),
):
    return service.create(project_id, data)


@router.get("/projects/{project_id}/terrains", response_model=list[TerrainRead])
def list_terrains(project_id: int, service: TerrainService = Depends(get_service)):
    return service.list(project_id)


@router.get("/terrains/{terrain_id}", response_model=TerrainRead)
def get_terrain(terrain_id: int, service: TerrainService = Depends(get_service)):
    return service.get(terrain_id)


@router.patch("/terrains/{terrain_id}", response_model=TerrainRead)
def update_terrain(
    terrain_id: int,
    data: TerrainUpdate,
    service: TerrainService = Depends(get_service),
):
    return service.update(terrain_id, data)


@router.delete("/terrains/{terrain_id}", status_code=204)
def delete_terrain(terrain_id: int, service: TerrainService = Depends(get_service)):
    service.delete(terrain_id)
    return Response(status_code=204)
