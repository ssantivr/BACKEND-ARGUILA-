from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require
from app.database import get_session
from app.dtos import (
    RenovationLogCreate,
    RenovationLogRead,
    RenovationLogUpdate,
    RenovationStatus,
    WalkthroughRead,
    WalkthroughStepCreate,
    WalkthroughStepRead,
    WalkthroughStepUpdate,
)
from app.models import User
from app.services.walkthrough_service import WalkthroughService

router = APIRouter(prefix="/interior-walkthrough", tags=["interior walkthrough"])


def reader(
    session: Session = Depends(get_session),
    user: User = Depends(require("walkthrough:read")),
) -> WalkthroughService:
    return WalkthroughService(session, user)


def writer(
    session: Session = Depends(get_session),
    user: User = Depends(require("walkthrough:write")),
) -> WalkthroughService:
    return WalkthroughService(session, user)


@router.get("", response_model=WalkthroughRead)
def read_walkthrough(project_id: int, service: WalkthroughService = Depends(reader)):
    return service.read(project_id)


@router.post("/steps", response_model=WalkthroughStepRead, status_code=status.HTTP_201_CREATED)
def create_step(data: WalkthroughStepCreate, service: WalkthroughService = Depends(writer)):
    return service.create_step(data)


@router.patch("/steps/{step_id}", response_model=WalkthroughStepRead)
def update_step(
    step_id: int,
    data: WalkthroughStepUpdate,
    service: WalkthroughService = Depends(writer),
):
    return service.update_step(step_id, data)


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(step_id: int, service: WalkthroughService = Depends(writer)):
    service.delete_step(step_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/logs", response_model=list[RenovationLogRead])
def list_logs(
    project_id: int,
    room_id: int | None = None,
    status: RenovationStatus | None = None,
    service: WalkthroughService = Depends(reader),
):
    return service.list_logs(project_id, room_id, status)


@router.post("/logs", response_model=RenovationLogRead, status_code=status.HTTP_201_CREATED)
def create_log(data: RenovationLogCreate, service: WalkthroughService = Depends(writer)):
    return service.create_log(data)


@router.patch("/logs/{log_id}", response_model=RenovationLogRead)
def update_log(
    log_id: int,
    data: RenovationLogUpdate,
    service: WalkthroughService = Depends(writer),
):
    return service.update_log(log_id, data)


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(log_id: int, service: WalkthroughService = Depends(writer)):
    service.delete_log(log_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
