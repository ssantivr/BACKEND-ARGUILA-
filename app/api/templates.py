from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import ProjectRead, TemplateRead
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])


def get_service(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> TemplateService:
    return TemplateService(session, user)


@router.get("", response_model=list[TemplateRead])
def list_templates(service: TemplateService = Depends(get_service)):
    return [
        TemplateRead(
            id=template.id,
            name=template.name,
            kind=template.kind,
            description=template.description,
            levels=len(template.levels),
            lot_area_m2=template.lot_area_m2,
            built_area_m2=template.built_area_m2,
        )
        for template in service.list()
    ]


@router.post(
    "/{template_id}/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project_from_template(
    template_id: str, service: TemplateService = Depends(get_service)
):
    return service.create_project(template_id)
