from dataclasses import dataclass, field
from typing import Any, Protocol

Point = tuple[float, float, float]


class ProviderDataError(ValueError):
    """The document does not follow the provider's format. The message is shown to the user."""


@dataclass(frozen=True)
class ElementDraft:
    """A spatial element in ARQUILA coordinates: metres, x and y on the plan, z upwards."""

    external_id: str
    name: str
    minimum: Point
    maximum: Point
    kind: str = "mesh"
    layer: str | None = None
    work_status: str | None = None
    mesh_ref: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


class SpatialDataProvider(Protocol):
    """Adapter that turns one external CAD or 3D format into element drafts."""

    name: str

    def read(self, document: dict[str, Any]) -> list[ElementDraft]: ...
