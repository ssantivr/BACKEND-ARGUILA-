from dataclasses import dataclass

COLUMN_SIDE_M = 0.3


@dataclass(frozen=True)
class TemplateRoom:
    name: str
    x_m: float
    y_m: float
    width_m: float
    depth_m: float


@dataclass(frozen=True)
class TemplateLevel:
    title: str
    level: str
    height_m: float
    rooms: tuple[TemplateRoom, ...]

    @property
    def area_m2(self) -> float:
        return sum(room.width_m * room.depth_m for room in self.rooms)


@dataclass(frozen=True)
class ProjectTemplate:
    id: str
    name: str
    kind: str
    description: str
    location: str | None
    lot_width_m: float
    lot_length_m: float
    slope_percent: float
    soil_type: str
    levels: tuple[TemplateLevel, ...]

    @property
    def lot_area_m2(self) -> float:
        return self.lot_width_m * self.lot_length_m

    @property
    def built_area_m2(self) -> float:
        return sum(level.area_m2 for level in self.levels)


def row(y_m: float, depth_m: float, start_x_m: float, *rooms: tuple[str, float]) -> tuple[TemplateRoom, ...]:
    placed = []
    x_m = start_x_m

    for name, width_m in rooms:
        placed.append(TemplateRoom(name, x_m, y_m, width_m, depth_m))
        x_m += width_m

    return tuple(placed)


def apartment_floor(title: str, level: str) -> TemplateLevel:
    return TemplateLevel(
        title,
        level,
        2.8,
        row(4, 6, 2.5, ("Apto. A · social", 6.5), ("Circulación", 2), ("Apto. B · social", 6.5))
        + row(10, 6, 2.5, ("Apto. A · habitaciones", 6.5), ("Escalera", 2), ("Apto. B · habitaciones", 6.5)),
    )


TEMPLATES: tuple[ProjectTemplate, ...] = (
    ProjectTemplate(
        id="casa-familiar-andina",
        name="Casa Familiar Andina",
        kind="Casa",
        description="Vivienda unifamiliar de dos niveles con estudio, lavandería y jardín posterior.",
        location="Pasto, Nariño",
        lot_width_m=16,
        lot_length_m=24,
        slope_percent=8,
        soil_type="Franco arcilloso",
        levels=(
            TemplateLevel(
                "Planta baja",
                "0",
                2.8,
                row(5, 4, 1, ("Sala", 6), ("Hall", 2.5), ("Comedor", 5.5))
                + row(
                    9,
                    4,
                    1,
                    ("Cocina", 5),
                    ("Escalera", 2.2),
                    ("Baño social", 1.8),
                    ("Lavandería", 2.2),
                    ("Estudio", 2.8),
                ),
            ),
            TemplateLevel(
                "Planta alta",
                "1",
                2.8,
                row(5, 3.5, 1, ("Hab. principal", 5), ("Estar íntimo", 4), ("Habitación 2", 4))
                + row(
                    8.5,
                    3.5,
                    1,
                    ("Baño principal", 3),
                    ("Escalera", 2.5),
                    ("Baño", 3),
                    ("Habitación 3", 4.5),
                ),
            ),
        ),
    ),
    ProjectTemplate(
        id="vivienda-compacta",
        name="Vivienda compacta",
        kind="Casa",
        description="Casa de un nivel para lote medianero, con dos habitaciones y patio.",
        location=None,
        lot_width_m=8,
        lot_length_m=20,
        slope_percent=2,
        soil_type="Limo arenoso",
        levels=(
            TemplateLevel(
                "Planta única",
                "0",
                2.7,
                row(3, 4, 0, ("Sala comedor", 5), ("Cocina", 3))
                + row(7, 4, 0, ("Habitación 1", 4), ("Baño", 1.6), ("Hall", 2.4))
                + row(11, 4, 0, ("Habitación 2", 4.5), ("Lavandería", 3.5)),
            ),
        ),
    ),
    ProjectTemplate(
        id="edificio-multifamiliar",
        name="Edificio multifamiliar",
        kind="Edificio residencial",
        description="Edificio residencial de tres pisos con apartamentos tipo y circulación central.",
        location=None,
        lot_width_m=20,
        lot_length_m=25,
        slope_percent=3,
        soil_type="Grava arcillosa",
        levels=(
            apartment_floor("Piso 1", "0"),
            apartment_floor("Piso 2", "1"),
            apartment_floor("Piso 3", "2"),
        ),
    ),
    ProjectTemplate(
        id="oficina-profesional",
        name="Oficina profesional",
        kind="Oficina",
        description="Sede de dos niveles para consultorios u oficinas con recepción y sala de juntas.",
        location=None,
        lot_width_m=18,
        lot_length_m=22,
        slope_percent=1,
        soil_type="Arcilla compacta",
        levels=(
            TemplateLevel(
                "Planta baja",
                "0",
                3,
                row(4, 5, 2.5, ("Recepción", 6), ("Sala de espera", 7))
                + row(9, 5, 2.5, ("Consultorio 1", 4.5), ("Consultorio 2", 4.5), ("Baños", 4)),
            ),
            TemplateLevel(
                "Planta alta",
                "1",
                3,
                row(4, 5, 2.5, ("Sala de juntas", 7), ("Oficina abierta", 6))
                + row(9, 5, 2.5, ("Oficina 1", 4.5), ("Oficina 2", 4.5), ("Archivo y baños", 4)),
            ),
        ),
    ),
)


def corner_columns(level: TemplateLevel) -> list[tuple[float, float]]:
    min_x = min(room.x_m for room in level.rooms)
    min_y = min(room.y_m for room in level.rooms)
    max_x = max(room.x_m + room.width_m for room in level.rooms) - COLUMN_SIDE_M
    max_y = max(room.y_m + room.depth_m for room in level.rooms) - COLUMN_SIDE_M

    return [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
