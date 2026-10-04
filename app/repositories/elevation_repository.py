from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Elevation


class ElevationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, elevation_id: int) -> Elevation | None:
        return self.session.get(Elevation, elevation_id)

    def list_by_project(self, project_id: int, orientation: str | None = None) -> list[Elevation]:
        query = select(Elevation).where(Elevation.project_id == project_id)

        if orientation is not None:
            query = query.where(Elevation.orientation == orientation)

        return list(self.session.scalars(query.order_by(Elevation.id)))

    def save(self, elevation: Elevation) -> Elevation:
        self.session.add(elevation)
        self.session.commit()
        self.session.refresh(elevation)
        return elevation

    def delete(self, elevation: Elevation) -> None:
        self.session.delete(elevation)
        self.session.commit()
