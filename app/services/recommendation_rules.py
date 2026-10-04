from collections.abc import Iterator, Sequence

from app.models import Material, Terrain

STEEP_SLOPE_PERCENT = 15
CLAY_SOIL_NAMES = {"clay", "arcilla", "arcilloso"}

Suggestion = tuple[str, str, str]


def number(value) -> str:
    return f"{float(value):g}".replace(".", ",")


def terrain_suggestions(terrains: Sequence[Terrain]) -> Iterator[Suggestion]:
    if not terrains:
        yield (
            "terrain",
            "Registra al menos un terreno para poder analizar el proyecto.",
            "high",
        )
        return

    for terrain in terrains:
        missing = []

        if terrain.slope_percent is None:
            missing.append("la pendiente")

        if not terrain.soil_type:
            missing.append("el tipo de suelo")

        if missing:
            yield (
                "terrain",
                f"Completa {' y '.join(missing)} del terreno "
                f'"{terrain.name}" para poder evaluarlo.',
                "medium",
            )

        if terrain.slope_percent is not None and terrain.slope_percent >= STEEP_SLOPE_PERCENT:
            yield (
                "terrain",
                f'El terreno "{terrain.name}" tiene una pendiente de '
                f"{number(terrain.slope_percent)} %. Considera muros de contención, "
                f"terrazas y un estudio de estabilidad antes de diseñar.",
                "high",
            )

        if (terrain.soil_type or "").strip().lower() in CLAY_SOIL_NAMES:
            yield (
                "terrain",
                f'El terreno "{terrain.name}" tiene suelo arcilloso. Conviene un '
                f"estudio de suelos para definir la cimentación y el drenaje.",
                "high",
            )


def material_suggestions(materials: Sequence[Material]) -> Iterator[Suggestion]:
    if not materials:
        yield (
            "materials",
            "Aún no hay materiales registrados. Agrégalos para estimar el costo.",
            "low",
        )
        return

    without_cost = [m.name for m in materials if m.unit_cost == 0]

    if without_cost:
        yield (
            "materials",
            "Estos materiales no tienen costo unitario, así que el costo total "
            "está subestimado: " + ", ".join(without_cost) + ".",
            "medium",
        )

    without_quantity = [m.name for m in materials if m.quantity == 0]

    if without_quantity:
        yield (
            "materials",
            "Estos materiales tienen cantidad cero: " + ", ".join(without_quantity) + ".",
            "low",
        )


def evaluate(terrains: Sequence[Terrain], materials: Sequence[Material]) -> list[Suggestion]:
    return [*terrain_suggestions(terrains), *material_suggestions(materials)]
