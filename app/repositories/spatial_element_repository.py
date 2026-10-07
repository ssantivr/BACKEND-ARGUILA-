from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SpatialElement

Footprint = tuple[float, float, float, float]


class SpatialElementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, element_id: int) -> SpatialElement | None:
        return self.session.get(SpatialElement, element_id)

    def list_by_project(
        self,
        project_id: int,
        layer: str | None = None,
        room_id: int | None = None,
        work_status: str | None = None,
        footprint: Footprint | None = None,
    ) -> list[SpatialElement]:
        query = select(SpatialElement).where(SpatialElement.project_id == project_id)

        if layer is not None:
            query = query.where(SpatialElement.layer == layer)

        if room_id is not None:
            query = query.where(SpatialElement.room_id == room_id)

        if work_status is not None:
            query = query.where(SpatialElement.work_status == work_status)

        if footprint is not None:
            query = query.where(self._overlaps(footprint))

        return list(self.session.scalars(query.order_by(SpatialElement.id)))

    def by_external_id(self, project_id: int, source: str) -> dict[str, SpatialElement]:
        query = select(SpatialElement).where(
            SpatialElement.project_id == project_id,
            SpatialElement.source == source,
            SpatialElement.external_id.is_not(None),
        )

        return {element.external_id: element for element in self.session.scalars(query)}

    def save(self, element: SpatialElement) -> SpatialElement:
        self.session.add(element)
        self.session.commit()
        self.session.refresh(element)
        return element

    def save_all(self, elements: list[SpatialElement]) -> list[SpatialElement]:
        self.session.add_all(elements)
        self.session.commit()

        for element in elements:
            self.session.refresh(element)

        return elements

    def delete(self, element: SpatialElement) -> None:
        self.session.delete(element)
        self.session.commit()

    def _overlaps(self, footprint: Footprint):
        min_x, min_y, max_x, max_y = footprint

        # PostgreSQL answers this from the GiST index idx_spatial_elements_footprint, which is
        # built on exactly this box expression.
        if self.session.get_bind().dialect.name == "postgresql":
            stored = func.box(
                func.point(SpatialElement.min_x_m, SpatialElement.min_y_m),
                func.point(SpatialElement.max_x_m, SpatialElement.max_y_m),
            )

            return stored.op("&&")(func.box(func.point(min_x, min_y), func.point(max_x, max_y)))

        return (
            (SpatialElement.min_x_m <= max_x)
            & (SpatialElement.max_x_m >= min_x)
            & (SpatialElement.min_y_m <= max_y)
            & (SpatialElement.max_y_m >= min_y)
        )
