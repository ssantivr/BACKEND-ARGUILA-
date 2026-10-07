from collections import Counter
from typing import get_args

from sqlalchemy.orm import Session

from app.dtos import (
    COORDINATE_LIMIT_M,
    Layer,
    SpatialDataRead,
    SpatialElementCreate,
    SpatialElementUpdate,
    SpatialImportRead,
    SpatialImportRequest,
    WorkStatus,
    limit_config_size,
)
from app.errors import InvalidDataError, NotFoundError
from app.models import SpatialElement, User
from app.providers import PROVIDERS, ElementDraft, ProviderDataError
from app.repositories.spatial_element_repository import Footprint, SpatialElementRepository
from app.services.base import ApiScopedService, changes_in

LAYERS = get_args(Layer)
WORK_STATUSES = get_args(WorkStatus)
AXES = ("x", "y", "z")
MAX_IMPORTED_ELEMENTS = 2000
MIN_SIZE_M = 0.01
NAME_LENGTH = 160
KIND_LENGTH = 40
EXTERNAL_ID_LENGTH = 120
MESH_REF_LENGTH = 500


class SpatialService(ApiScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.elements = SpatialElementRepository(session)

    def read(
        self,
        project_id: int,
        layer: str | None = None,
        room_id: int | None = None,
        work_status: str | None = None,
        footprint: Footprint | None = None,
    ) -> SpatialDataRead:
        self._require_project(project_id)

        elements = self.elements.list_by_project(project_id, layer, room_id, work_status, footprint)
        found = Counter(element.layer for element in elements)

        return SpatialDataRead(
            project_id=project_id,
            counts={name: found[name] for name in LAYERS},
            elements=elements,
        )

    def create(self, data: SpatialElementCreate) -> SpatialElement:
        self._require_project(data.project_id)

        if data.room_id is not None:
            self._require_room(data.room_id, data.project_id)

        return self.elements.save(SpatialElement(**data.model_dump()))

    def get(self, element_id: int) -> SpatialElement:
        element = self.elements.get(element_id)

        if element is None or not self._owns(element.project_id):
            raise NotFoundError("Elemento espacial no encontrado.")

        return element

    def update(self, element_id: int, data: SpatialElementUpdate) -> SpatialElement:
        element = self.get(element_id)
        changes = changes_in(data, nullable={"room_id", "mesh_ref"})

        if changes.get("room_id") is not None:
            self._require_room(changes["room_id"], element.project_id)

        for field, value in changes.items():
            setattr(element, field, value)

        for axis in AXES:
            if getattr(element, f"max_{axis}_m") <= getattr(element, f"min_{axis}_m"):
                self.session.rollback()
                raise InvalidDataError(f"max_{axis}_m debe ser mayor que min_{axis}_m.")

        return self.elements.save(element)

    def delete(self, element_id: int) -> None:
        self.elements.delete(self.get(element_id))

    def import_document(self, data: SpatialImportRequest) -> SpatialImportRead:
        self._require_project(data.project_id)

        provider = PROVIDERS.get(data.provider)

        if provider is None:
            raise NotFoundError(
                "Proveedor de datos no admitido. Opciones: " + ", ".join(sorted(PROVIDERS)) + "."
            )

        try:
            drafts = provider.read(data.document)
        except ProviderDataError as error:
            raise InvalidDataError(str(error)) from None
        except (AttributeError, IndexError, KeyError, TypeError):
            # The document comes from outside: a shape the adapter did not expect is the
            # sender's mistake, not a server failure.
            raise InvalidDataError("El documento no tiene el formato esperado.") from None

        if not drafts:
            raise InvalidDataError("El documento no contiene elementos con geometría.")

        if len(drafts) > MAX_IMPORTED_ELEMENTS:
            raise InvalidDataError(
                f"El documento supera el límite de {MAX_IMPORTED_ELEMENTS} elementos."
            )

        known = self.elements.by_external_id(data.project_id, provider.name)
        created = 0
        elements = []

        for draft in drafts:
            values = self._values(draft, data)
            element = known.get(values["external_id"])

            if element is None:
                element = SpatialElement(project_id=data.project_id, source=provider.name)
                known[values["external_id"]] = element
                created += 1

            for field, value in values.items():
                setattr(element, field, value)

            elements.append(element)

        saved = self.elements.save_all(list(dict.fromkeys(elements)))

        return SpatialImportRead(
            provider=provider.name,
            created=created,
            updated=len(saved) - created,
            elements=saved,
        )

    def _values(self, draft: ElementDraft, data: SpatialImportRequest) -> dict:
        values = {
            "external_id": draft.external_id[:EXTERNAL_ID_LENGTH],
            "name": draft.name[:NAME_LENGTH],
            "kind": draft.kind[:KIND_LENGTH],
            "layer": draft.layer if draft.layer in LAYERS else data.layer,
            "work_status": (
                draft.work_status if draft.work_status in WORK_STATUSES else data.work_status
            ),
            "mesh_ref": None if draft.mesh_ref is None else str(draft.mesh_ref)[:MESH_REF_LENGTH],
            "config": draft.config,
        }

        try:
            limit_config_size(draft.config)
        except ValueError as error:
            raise InvalidDataError(f"«{values['name']}»: {error}") from None

        for axis, low, high in zip(AXES, draft.minimum, draft.maximum, strict=True):
            low, high = round(min(low, high), 2), round(max(low, high), 2)

            if max(abs(low), abs(high)) > COORDINATE_LIMIT_M:
                raise InvalidDataError(
                    f"«{values['name']}» queda fuera del rango admitido de coordenadas."
                )

            # Flat geometry, such as a floor finish, still needs a box the database accepts.
            values[f"min_{axis}_m"] = low
            values[f"max_{axis}_m"] = max(high, round(low + MIN_SIZE_M, 2))

        return values
