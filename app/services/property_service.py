from sqlalchemy.orm import Session

from app.dtos import PropertyCreate, PropertyUpdate, UnitCreate, UnitUpdate
from app.errors import ConflictError, NotFoundError
from app.models import Property, Unit, User
from app.repositories.property_repository import PropertyRepository, UnitRepository
from app.services.base import ApiScopedService, changes_in


class PropertyService(ApiScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.properties = PropertyRepository(session)

    def create(self, data: PropertyCreate) -> Property:
        self._require_project(data.project_id)
        self._ensure_name_is_free(data.project_id, data.name)

        return self.properties.save(Property(**data.model_dump()))

    def list(self, project_id: int | None = None) -> list[Property]:
        return self.properties.list_by_owner(self.user.id, project_id)

    def get(self, property_id: int) -> Property:
        item = self.properties.get(property_id)

        if item is None or not self._owns(item.project_id):
            raise NotFoundError("Propiedad no encontrada.")

        return item

    def update(self, property_id: int, data: PropertyUpdate) -> Property:
        item = self.get(property_id)
        changes = changes_in(data, nullable={"address"})

        if changes.get("name", item.name) != item.name:
            self._ensure_name_is_free(item.project_id, changes["name"])

        for field, value in changes.items():
            setattr(item, field, value)

        return self.properties.save(item)

    def delete(self, property_id: int) -> None:
        self.properties.delete(self.get(property_id))

    def _ensure_name_is_free(self, project_id: int, name: str) -> None:
        if self.properties.get_by_name(project_id, name) is not None:
            raise ConflictError("El proyecto ya tiene una propiedad con ese nombre.")


class UnitService(ApiScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.properties = PropertyService(session, user)
        self.units = UnitRepository(session)

    def create(self, data: UnitCreate) -> Unit:
        self.properties.get(data.property_id)
        self._ensure_code_is_free(data.property_id, data.code)

        return self.units.save(Unit(**data.model_dump()))

    def list(
        self,
        project_id: int | None = None,
        property_id: int | None = None,
        status: str | None = None,
    ) -> list[Unit]:
        return self.units.list_by_owner(self.user.id, project_id, property_id, status)

    def get(self, unit_id: int) -> Unit:
        unit = self.units.get(unit_id)

        if unit is None:
            raise NotFoundError("Unidad no encontrada.")

        try:
            self.properties.get(unit.property_id)
        except NotFoundError:
            raise NotFoundError("Unidad no encontrada.") from None

        return unit

    def project_of(self, unit_id: int) -> int:
        return self.properties.get(self.get(unit_id).property_id).project_id

    def update(self, unit_id: int, data: UnitUpdate) -> Unit:
        unit = self.get(unit_id)
        changes = changes_in(data, nullable={"price", "area_m2", "model_asset_ref"})

        if changes.get("code", unit.code) != unit.code:
            self._ensure_code_is_free(unit.property_id, changes["code"])

        for field, value in changes.items():
            setattr(unit, field, value)

        return self.units.save(unit)

    def delete(self, unit_id: int) -> None:
        self.units.delete(self.get(unit_id))

    def _ensure_code_is_free(self, property_id: int, code: str) -> None:
        if self.units.get_by_code(property_id, code) is not None:
            raise ConflictError("La propiedad ya tiene una unidad con ese código.")
