from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import User
from app.repositories.project_repository import ProjectRepository


class ProjectScopedService:
    def __init__(self, session: Session, user: User) -> None:
        self.session = session
        self.user = user
        self.projects = ProjectRepository(session)

    def _owns(self, project_id: int) -> bool:
        return self.projects.get_owned(project_id, self.user.id) is not None

    def _ensure_project_exists(self, project_id: int) -> None:
        if not self._owns(project_id):
            raise NotFoundError("Project not found")
