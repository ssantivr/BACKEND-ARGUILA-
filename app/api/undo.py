from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import DeletedItemRead
from app.services.undo_service import UndoService

router = APIRouter(tags=["undo"])


def get_service(session: Session = Depends(get_session)) -> UndoService:
    return UndoService(session)


@router.get("/projects/{project_id}/undo", response_model=list[DeletedItemRead])
def list_undoable_deletions(
    project_id: int, service: UndoService = Depends(get_service)
):
    return service.list(project_id)


@router.post("/projects/{project_id}/undo", response_model=DeletedItemRead)
def undo_last_deletion(project_id: int, service: UndoService = Depends(get_service)):
    return service.undo_last(project_id)
