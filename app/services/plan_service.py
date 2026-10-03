from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Plan
from app.repositories.plan_repository import PlanRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import PlanCreate, PlanUpdate


class PlanService:
    def __init__(self, session: Session) -> None:
        self.plans = PlanRepository(session)
        self.projects = ProjectRepository(session)

    def create(self, project_id: int, data: PlanCreate) -> Plan:
        self._ensure_project_exists(project_id)

        return self.plans.save(Plan(project_id=project_id, **data.model_dump()))

    def list(self, project_id: int) -> list[Plan]:
        self._ensure_project_exists(project_id)

        return self.plans.list_by_project(project_id)

    def get(self, plan_id: int) -> Plan:
        plan = self.plans.get(plan_id)

        if plan is None:
            raise NotFoundError("Plan not found")

        return plan

    def update(self, plan_id: int, data: PlanUpdate) -> Plan:
        plan = self.get(plan_id)
        changes = data.model_dump(exclude_unset=True)

        # title is NOT NULL: an explicit null means "leave unchanged"
        if changes.get("title", "") is None:
            del changes["title"]

        for field, value in changes.items():
            setattr(plan, field, value)

        return self.plans.save(plan)

    def delete(self, plan_id: int) -> None:
        self.plans.delete(self.get(plan_id))

    def _ensure_project_exists(self, project_id: int) -> None:
        if self.projects.get(project_id) is None:
            raise NotFoundError("Project not found")
