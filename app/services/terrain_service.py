from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Terrain, User
from app.repositories.terrain_repository import TerrainRepository
from app.schemas import TerrainCreate, TerrainUpdate
from app.services.base import ProjectScopedService
from app.services.undo_history import snapshot, undo_history


class TerrainService(ProjectScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.terrains = TerrainRepository(session)

    def create(self, project_id: int, data: TerrainCreate) -> Terrain:
        self._ensure_project_exists(project_id)

        return self.terrains.save(Terrain(project_id=project_id, **data.model_dump()))

    def list(self, project_id: int) -> list[Terrain]:
        self._ensure_project_exists(project_id)

        return self.terrains.list_by_project(project_id)

    def get(self, terrain_id: int) -> Terrain:
        terrain = self.terrains.get(terrain_id)

        if terrain is None or not self._owns(terrain.project_id):
            raise NotFoundError("Terrain not found")

        return terrain

    def update(self, terrain_id: int, data: TerrainUpdate) -> Terrain:
        terrain = self.get(terrain_id)
        changes = data.model_dump(exclude_unset=True)

        # name and area_m2 are NOT NULL: an explicit null means "leave unchanged"
        for required in ("name", "area_m2"):
            if changes.get(required, "") is None:
                del changes[required]

        for field, value in changes.items():
            setattr(terrain, field, value)

        return self.terrains.save(terrain)

    def delete(self, terrain_id: int) -> None:
        terrain = self.get(terrain_id)
        deleted = snapshot("terrain", terrain.name, terrain)
        self.terrains.delete(terrain)
        undo_history.record(deleted)
