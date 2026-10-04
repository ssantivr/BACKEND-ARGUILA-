import unicodedata
from collections.abc import Sequence

from app.models import Material, Project, Terrain
from app.services import recommendation_rules
from app.services.recommendation_rules import number

GENTLE_SLOPE_PERCENT = 5

TOPIC_KEYWORDS = {
    "terrain": ("terreno", "lote", "pendiente", "suelo", "drenaje", "ciment", "desnivel"),
    "materials": ("material", "costo", "presupuesto", "precio", "cantidad", "cuanto"),
    "drawings": ("plano", "elevacion", "fachada", "nivel", "escala"),
}

HELP = (
    "Puedo responder sobre el terreno, los materiales y sus costos, y los planos "
    "y elevaciones. Pregunta por alguno de esos temas."
)


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def matched_topics(question: str) -> list[str]:
    normalized = normalize(question)

    return [
        topic
        for topic, keywords in TOPIC_KEYWORDS.items()
        if any(keyword in normalized for keyword in keywords)
    ]


def count(amount: int, singular: str, plural: str) -> str:
    return f"{amount} {singular if amount == 1 else plural}"


def money(value) -> str:
    return f"{float(value):,.2f}".translate(str.maketrans(",.", ".,"))


def describe_terrain(terrain: Terrain) -> str:
    sentences = [f'El terreno "{terrain.name}" tiene {number(terrain.area_m2)} m².']
    slope = terrain.slope_percent

    if slope is not None:
        if slope < GENTLE_SLOPE_PERCENT:
            sentences.append(
                f"Su pendiente de {number(slope)} % es suave y permite una sola "
                f"plataforma de cimentación."
            )
        elif slope < recommendation_rules.STEEP_SLOPE_PERCENT:
            sentences.append(
                f"Con {number(slope)} % de pendiente conviene escalonar la "
                f"construcción o prever un muro de contención en la parte alta, "
                f"y drenaje en la zona más baja."
            )

        if terrain.length_m is not None and slope > 0:
            drop = float(terrain.length_m) * float(slope) / 100
            sentences.append(f"El desnivel a lo largo del lote es de {number(round(drop, 2))} m.")

    if terrain.soil_type:
        sentences.append(f"Tipo de suelo registrado: {terrain.soil_type}.")

    return " ".join(sentences)


def terrain_answer(terrains: Sequence[Terrain]) -> str:
    lines = [describe_terrain(terrain) for terrain in terrains]
    lines.extend(content for _, content in recommendation_rules.terrain_suggestions(terrains))

    return "\n".join(lines)


def materials_answer(materials: Sequence[Material]) -> str:
    lines = []

    if materials:
        total = sum(material.quantity * material.unit_cost for material in materials)
        costliest = max(materials, key=lambda material: material.quantity * material.unit_cost)
        lines.append(
            f"Hay {count(len(materials), 'material registrado', 'materiales registrados')} "
            f"con un costo total de {money(total)}. El de mayor costo es "
            f"{costliest.name} ({money(costliest.quantity * costliest.unit_cost)})."
        )

    lines.extend(content for _, content in recommendation_rules.material_suggestions(materials))

    return "\n".join(lines)


def drawings_answer(project: Project) -> str:
    if not project.plans and not project.elevations:
        return "Aún no hay planos ni elevaciones registrados en el proyecto."

    lines = []

    if project.plans:
        lines.append("Planos: " + ", ".join(plan.title for plan in project.plans) + ".")

    if project.elevations:
        lines.append(
            "Elevaciones: "
            + ", ".join(elevation.title for elevation in project.elevations)
            + "."
        )

    return "\n".join(lines)


def overview(
    project: Project, terrains: Sequence[Terrain], materials: Sequence[Material]
) -> str:
    parts = [
        count(len(terrains), "terreno", "terrenos"),
        count(len(materials), "material", "materiales"),
        count(len(project.plans), "plano", "planos"),
        count(len(project.elevations), "elevación", "elevaciones"),
    ]

    return (
        f'El proyecto "{project.name}" tiene {", ".join(parts[:-1])} y {parts[-1]}. '
        + HELP
    )


def answer(
    question: str,
    project: Project,
    terrains: Sequence[Terrain],
    materials: Sequence[Material],
) -> str:
    answers = {
        "terrain": lambda: terrain_answer(terrains),
        "materials": lambda: materials_answer(materials),
        "drawings": lambda: drawings_answer(project),
    }
    topics = matched_topics(question)

    if not topics:
        return overview(project, terrains, materials)

    return "\n\n".join(answers[topic]() for topic in topics)
