from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Project
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas import ProjectCreate, ProjectUpdate
from app.services.undo_history import undo_history


class ProjectService:
    def __init__(self, session: Session) -> None:
        self.projects = ProjectRepository(session)
        self.users = UserRepository(session)

    def create(self, data: ProjectCreate) -> Project:
        if self.users.get(data.owner_id) is None:
            raise NotFoundError("Owner not found")

        self._ensure_name_is_free(data.owner_id, data.name)

        return self.projects.save(Project(**data.model_dump()))

    def list(
        self,
        owner_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[Project]:
        return self.projects.list(owner_id=owner_id, status=status, search=search)

    def get(self, project_id: int) -> Project:
        project = self.projects.get(project_id)

        if project is None:
            raise NotFoundError("Project not found")

        return project

    def update(self, project_id: int, data: ProjectUpdate) -> Project:
        project = self.get(project_id)
        changes = data.model_dump(exclude_unset=True)

        # name and status are NOT NULL: an explicit null means "leave unchanged"
        for required in ("name", "status"):
            if changes.get(required, "") is None:
                del changes[required]

        if "name" in changes and changes["name"] != project.name:
            self._ensure_name_is_free(project.owner_id, changes["name"])

        for field, value in changes.items():
            setattr(project, field, value)

        return self.projects.save(project)

    def delete(self, project_id: int) -> None:
        self.projects.delete(self.get(project_id))
        undo_history.forget(project_id)

    def _ensure_name_is_free(self, owner_id: int, name: str) -> None:
        if self.projects.get_by_owner_and_name(owner_id, name) is not None:
            raise ConflictError("Owner already has a project with this name")
