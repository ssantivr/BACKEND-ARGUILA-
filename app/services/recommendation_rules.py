"""Rule-based project checks.

Each rule inspects the project data and yields (category, content) pairs. The
content is user-facing, so it is written in Spanish like the rest of the UI.
These are generic rules of thumb to prompt a review, not engineering advice.
"""

from collections.abc import Iterator, Sequence

from app.models import Material, Terrain

STEEP_SLOPE_PERCENT = 15
CLAY_SOIL_NAMES = {"clay", "arcilla", "arcilloso"}

Suggestion = tuple[str, str]


def terrain_suggestions(terrains: Sequence[Terrain]) -> Iterator[Suggestion]:
    if not terrains:
        yield (
            "terrain",
            "Registra al menos un terreno para poder analizar el proyecto.",
        )
        return

    for terrain in terrains:
        if terrain.slope_percent is None or not terrain.soil_type:
            yield (
                "terrain",
                f"Completa la pendiente y el tipo de suelo del terreno "
                f'"{terrain.name}" para poder evaluarlo.',
            )

        if (
            terrain.slope_percent is not None
            and terrain.slope_percent >= STEEP_SLOPE_PERCENT
        ):
            yield (
                "terrain",
                f'El terreno "{terrain.name}" tiene una pendiente de '
                f"{float(terrain.slope_percent):g} %. Considera muros de contención, "
                f"terrazas y un estudio de estabilidad antes de diseñar.",
            )

        if (terrain.soil_type or "").strip().lower() in CLAY_SOIL_NAMES:
            yield (
                "terrain",
                f'El terreno "{terrain.name}" tiene suelo arcilloso. Conviene un '
                f"estudio de suelos para definir la cimentación y el drenaje.",
            )


def material_suggestions(materials: Sequence[Material]) -> Iterator[Suggestion]:
    if not materials:
        yield (
            "materials",
            "Aún no hay materiales registrados. Agrégalos para estimar el costo.",
        )
        return

    without_cost = [m.name for m in materials if m.unit_cost == 0]

    if without_cost:
        yield (
            "materials",
            "Estos materiales no tienen costo unitario, así que el costo total "
            "está subestimado: " + ", ".join(without_cost) + ".",
        )

    without_quantity = [m.name for m in materials if m.quantity == 0]

    if without_quantity:
        yield (
            "materials",
            "Estos materiales tienen cantidad cero: "
            + ", ".join(without_quantity)
            + ".",
        )


def evaluate(
    terrains: Sequence[Terrain], materials: Sequence[Material]
) -> list[Suggestion]:
    return [*terrain_suggestions(terrains), *material_suggestions(materials)]
