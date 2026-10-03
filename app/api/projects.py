from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import ProjectCreate, ProjectRead, ProjectStatus, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_service(session: Session = Depends(get_session)) -> ProjectService:
    return ProjectService(session)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, service: ProjectService = Depends(get_service)):
    return service.create(data)


@router.get("", response_model=list[ProjectRead])
def list_projects(
    owner_id: int | None = None,
    status: ProjectStatus | None = None,
    search: str | None = None,
    service: ProjectService = Depends(get_service),
):
    return service.list(owner_id=owner_id, status=status, search=search)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, service: ProjectService = Depends(get_service)):
    return service.get(project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    service: ProjectService = Depends(get_service),
):
    return service.update(project_id, data)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, service: ProjectService = Depends(get_service)):
    service.delete(project_id)
    return Response(status_code=204)
