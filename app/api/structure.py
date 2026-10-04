from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import StructureRead
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
