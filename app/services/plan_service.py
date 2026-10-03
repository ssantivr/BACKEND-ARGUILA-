from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Plan
from app.repositories.file_repository import FileRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import PlanCreate, PlanUpdate
from app.services.undo_history import snapshot, undo_history


class PlanService:
    def __init__(self, session: Session) -> None:
        self.plans = PlanRepository(session)
        self.files = FileRepository(session)
        self.projects = ProjectRepository(session)

    def create(self, project_id: int, data: PlanCreate) -> Plan:
        self._ensure_project_exists(project_id)
        self._ensure_file_in_project(data.file_id, project_id)

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

        # file_id is nullable: an explicit null detaches the file
        self._ensure_file_in_project(changes.get("file_id"), plan.project_id)

        for field, value in changes.items():
            setattr(plan, field, value)

        return self.plans.save(plan)

    def delete(self, plan_id: int) -> None:
        plan = self.get(plan_id)
        deleted = snapshot("plan", plan.title, plan)
        self.plans.delete(plan)
        undo_history.record(deleted)

    def _ensure_file_in_project(self, file_id: int | None, project_id: int) -> None:
        if file_id is not None and self.files.get_in_project(file_id, project_id) is None:
            raise NotFoundError("File not found in this project")

    def _ensure_project_exists(self, project_id: int) -> None:
        if self.projects.get(project_id) is None:
            raise NotFoundError("Project not found")
