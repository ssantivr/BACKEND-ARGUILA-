from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, Property, Unit


class PropertyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, property_id: int) -> Property | None:
        return self.session.get(Property, property_id)

    def get_by_name(self, project_id: int, name: str) -> Property | None:
        return self.session.scalar(
            select(Property).where(Property.project_id == project_id, Property.name == name)
        )

    def list_by_owner(self, owner_id: int, project_id: int | None = None) -> list[Property]:
        query = select(Property).join(Project).where(Project.owner_id == owner_id)

        if project_id is not None:
            query = query.where(Property.project_id == project_id)

        return list(self.session.scalars(query.order_by(Property.id)))

    def save(self, item: Property) -> Property:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, item: Property) -> None:
        self.session.delete(item)
        self.session.commit()


class UnitRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, unit_id: int) -> Unit | None:
        return self.session.get(Unit, unit_id)

    def get_by_code(self, property_id: int, code: str) -> Unit | None:
        return self.session.scalar(
            select(Unit).where(Unit.property_id == property_id, Unit.code == code)
        )

    def list_by_owner(
        self,
        owner_id: int,
        project_id: int | None = None,
        property_id: int | None = None,
        status: str | None = None,
    ) -> list[Unit]:
        query = select(Unit).join(Property).join(Project).where(Project.owner_id == owner_id)

        if project_id is not None:
            query = query.where(Property.project_id == project_id)

        if property_id is not None:
            query = query.where(Unit.property_id == property_id)

        if status is not None:
            query = query.where(Unit.status == status)

        return list(self.session.scalars(query.order_by(Unit.floor_level, Unit.id)))

    def save(self, unit: Unit) -> Unit:
        self.session.add(unit)
        self.session.commit()
        self.session.refresh(unit)
        return unit

    def delete(self, unit: Unit) -> None:
        self.session.delete(unit)
        self.session.commit()
