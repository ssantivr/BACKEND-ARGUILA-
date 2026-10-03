from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import PlanCreate, PlanRead, PlanUpdate
from app.services.plan_service import PlanService

router = APIRouter(tags=["plans"])


def get_service(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PlanService:
    return PlanService(session, user)


@router.post(
    "/projects/{project_id}/plans",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
)
def create_plan(
    project_id: int,
    data: PlanCreate,
    service: PlanService = Depends(get_service),
):
    return service.create(project_id, data)


@router.get("/projects/{project_id}/plans", response_model=list[PlanRead])
def list_plans(project_id: int, service: PlanService = Depends(get_service)):
    return service.list(project_id)


@router.get("/plans/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: int, service: PlanService = Depends(get_service)):
    return service.get(plan_id)


@router.patch("/plans/{plan_id}", response_model=PlanRead)
def update_plan(
    plan_id: int,
    data: PlanUpdate,
    service: PlanService = Depends(get_service),
):
    return service.update(plan_id, data)


@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(plan_id: int, service: PlanService = Depends(get_service)):
    service.delete(plan_id)
    return Response(status_code=204)
