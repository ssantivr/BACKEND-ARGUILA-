from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Elevation
from app.repositories.elevation_repository import ElevationRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import ElevationCreate, ElevationUpdate
from app.services.undo_history import snapshot, undo_history


class ElevationService:
    def __init__(self, session: Session) -> None:
        self.elevations = ElevationRepository(session)
        self.files = FileRepository(session)
        self.projects = ProjectRepository(session)

    def create(self, project_id: int, data: ElevationCreate) -> Elevation:
        self._ensure_project_exists(project_id)
        self._ensure_file_in_project(data.file_id, project_id)

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

        changes = data.model_dump(exclude_unset=True)

        # title and orientation are NOT NULL: an explicit null means "leave unchanged"
        for required in ("title", "orientation"):
            if changes.get(required, "") is None:
                del changes[required]

        # file_id is nullable: an explicit null detaches the file
        self._ensure_file_in_project(changes.get("file_id"), elevation.project_id)

        for field, value in changes.items():
            setattr(elevation, field, value)

        return self.elevations.save(elevation)

    def delete(self, elevation_id: int) -> None:
        elevation = self.get(elevation_id)
        deleted = snapshot("elevation", elevation.title, elevation)
        self.elevations.delete(elevation)
        undo_history.record(deleted)

    def _ensure_file_in_project(self, file_id: int | None, project_id: int) -> None:
        if file_id is not None and self.files.get_in_project(file_id, project_id) is None:
            raise NotFoundError("File not found in this project")

    def _ensure_project_exists(self, project_id: int) -> None:
        if self.projects.get(project_id) is None:
            raise NotFoundError("Project not found")
