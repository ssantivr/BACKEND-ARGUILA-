from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Terrain, TerrainPoint, User
from app.repositories.terrain_repository import TerrainRepository
from app.schemas import TerrainCreate, TerrainPointData, TerrainUpdate
from app.services.base import ProjectScopedService
from app.services.undo_history import snapshot, undo_history


def build_points(points: list[TerrainPointData] | None) -> list[TerrainPoint]:
    return [
        TerrainPoint(position=position, x_m=point.x_m, y_m=point.y_m)
        for position, point in enumerate(points or [])
    ]


class TerrainService(ProjectScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.terrains = TerrainRepository(session)

    def create(self, project_id: int, data: TerrainCreate) -> Terrain:
        self._ensure_project_exists(project_id)

        values = data.model_dump(exclude={"points"})
        terrain = Terrain(project_id=project_id, **values)
        terrain.points = build_points(data.points)

        return self.terrains.save(terrain)

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

        for required in ("name", "area_m2"):
            if changes.get(required, "") is None:
                del changes[required]

        if "points" in changes:
            del changes["points"]
            terrain.points.clear()
            self.session.flush()
            terrain.points = build_points(data.points)

        for field, value in changes.items():
            setattr(terrain, field, value)

        return self.terrains.save(terrain)

    def delete(self, terrain_id: int) -> None:
        terrain = self.get(terrain_id)
        deleted = snapshot("terrain", terrain.name, terrain, ("points",))
        self.terrains.delete(terrain)
        undo_history.record(deleted, session=self.session)
