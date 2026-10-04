from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import ElementKind, RoofUpdate, StructureRead, SurfaceUpdate
from app.services.structure_service import StructureService

router = APIRouter(tags=["structure"])


def get_service(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> StructureService:
    return StructureService(session, user)


@router.get("/projects/{project_id}/structure", response_model=StructureRead)
def get_structure(project_id: int, service: StructureService = Depends(get_service)):
    return service.build(project_id)


@router.patch("/projects/{project_id}/structure/roof", status_code=status.HTTP_204_NO_CONTENT)
def set_roof(project_id: int, data: RoofUpdate, service: StructureService = Depends(get_service)):
    service.set_roof(project_id, data.roof)


@router.patch(
    "/projects/{project_id}/structure/{kind}/{element_id}/surface",
    status_code=status.HTTP_204_NO_CONTENT,
)
def set_surface(
    project_id: int,
    kind: ElementKind,
    element_id: int,
    data: SurfaceUpdate,
    service: StructureService = Depends(get_service),
):
    service.set_surface(project_id, kind, element_id, data.surface)
