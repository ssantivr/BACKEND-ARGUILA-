from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Elevation
from app.repositories.elevation_repository import ElevationRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import ElevationCreate, ElevationUpdate
from app.services.undo_history import snapshot, undo_history


class ElevationService:
    def __init__(self, session: Session) -> None:
        self.elevations = ElevationRepository(session)
        self.projects = ProjectRepository(session)

    def create(self, project_id: int, data: ElevationCreate) -> Elevation:
        self._ensure_project_exists(project_id)

        return self.elevations.save(
            Elevation(project_id=project_id, **data.model_dump())
        )

    def list(self, project_id: int, orientation: str | None = None) -> list[Elevation]:
        self._ensure_project_exists(project_id)

        return self.elevations.list_by_project(project_id, orientation=orientation)

    def get(self, elevation_id: int) -> Elevation:
        elevation = self.elevations.get(elevation_id)

        if elevation is None:
            raise NotFoundError("Elevation not found")

        return elevation

    def update(self, elevation_id: int, data: ElevationUpdate) -> Elevation:
        elevation = self.get(elevation_id)

        # both columns are NOT NULL: an explicit null means "leave unchanged"
        changes = data.model_dump(exclude_unset=True, exclude_none=True)

        for field, value in changes.items():
            setattr(elevation, field, value)

        return self.elevations.save(elevation)

    def delete(self, elevation_id: int) -> None:
        elevation = self.get(elevation_id)
        deleted = snapshot("elevation", elevation.title, elevation)
        self.elevations.delete(elevation)
        undo_history.record(deleted)

    def _ensure_project_exists(self, project_id: int) -> None:
        if self.projects.get(project_id) is None:
            raise NotFoundError("Project not found")
