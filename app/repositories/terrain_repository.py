from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Terrain


class TerrainRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, terrain_id: int) -> Terrain | None:
        return self.session.get(Terrain, terrain_id)

    def list_by_project(self, project_id: int) -> list[Terrain]:
        query = select(Terrain).where(Terrain.project_id == project_id)
        return list(self.session.scalars(query.order_by(Terrain.id)))

    def save(self, terrain: Terrain) -> Terrain:
        self.session.add(terrain)
        self.session.commit()
        self.session.refresh(terrain)
        return terrain

    def delete(self, terrain: Terrain) -> None:
        self.session.delete(terrain)
        self.session.commit()
