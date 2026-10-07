from typing import Any

from app.providers.base import ElementDraft, Point, ProviderDataError


def read_point(value: Any, label: str) -> Point:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or not all(isinstance(item, int | float) and not isinstance(item, bool) for item in value)
    ):
        raise ProviderDataError(f"{label} debe ser una lista de tres números [x, y, z].")

    return float(value[0]), float(value[1]), float(value[2])


class NativeJsonAdapter:
    """Reads ARQUILA's own exchange format: a list of elements with explicit bounds."""

    name = "native"

    def read(self, document: dict[str, Any]) -> list[ElementDraft]:
        elements = document.get("elements")

        if not isinstance(elements, list):
            raise ProviderDataError("El documento debe tener una lista «elements».")

        return [self._draft(item, index) for index, item in enumerate(elements)]

    def _draft(self, item: Any, index: int) -> ElementDraft:
        label = f"elements[{index}]"

        if not isinstance(item, dict):
            raise ProviderDataError(f"{label} debe ser un objeto.")

        bounds = item.get("bounds")

        if not isinstance(bounds, dict):
            raise ProviderDataError(f"{label}.bounds debe tener «min» y «max».")

        config = item.get("config", {})

        return ElementDraft(
            external_id=str(item.get("id", index)),
            name=str(item.get("name") or f"Elemento {index + 1}"),
            minimum=read_point(bounds.get("min"), f"{label}.bounds.min"),
            maximum=read_point(bounds.get("max"), f"{label}.bounds.max"),
            kind=str(item.get("kind") or "mesh"),
            layer=item.get("layer"),
            work_status=item.get("work_status"),
            mesh_ref=item.get("mesh_ref"),
            config=config if isinstance(config, dict) else {},
        )
