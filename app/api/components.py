from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import ComponentCreate, ComponentKind, ComponentRead, ComponentUpdate
from app.services.component_service import ComponentService

router = APIRouter(tags=["components"])


def get_service(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ComponentService:
    return ComponentService(session, user)


@router.post(
    "/projects/{project_id}/components",
    response_model=ComponentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_component(
    project_id: int,
    data: ComponentCreate,
    service: ComponentService = Depends(get_service),
):
    return service.create(project_id, data)


@router.get("/projects/{project_id}/components", response_model=list[ComponentRead])
def list_components(
    project_id: int,
    kind: ComponentKind | None = None,
    service: ComponentService = Depends(get_service),
):
    return service.list(project_id, kind)


@router.get("/components/{component_id}", response_model=ComponentRead)
def get_component(component_id: int, service: ComponentService = Depends(get_service)):
    return service.get(component_id)


@router.patch("/components/{component_id}", response_model=ComponentRead)
def update_component(
    component_id: int,
    data: ComponentUpdate,
    service: ComponentService = Depends(get_service),
):
    return service.update(component_id, data)


@router.delete("/components/{component_id}", status_code=204)
def delete_component(component_id: int, service: ComponentService = Depends(get_service)):
    service.delete(component_id)
    return Response(status_code=204)
