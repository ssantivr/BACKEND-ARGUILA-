from sqlalchemy.orm import Session

from app.models import Plan, Room, Terrain, User
from app.repositories.plan_repository import PlanRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.terrain_repository import TerrainRepository
from app.schemas import StructureRead, StructureRoom, StructureTerrain, TerrainPointData
from app.services.base import ProjectScopedService

STOREY_HEIGHT_M = 3.0
DEFAULT_SETBACK_M = 3.0
TERRAIN_GAP_M = 5.0

Outline = list[tuple[float, float]]
Lot = tuple[float, float, float]


def terrain_outline(terrain: Terrain) -> Outline | None:
    if len(terrain.points) >= 3:
        return [(float(point.x_m), float(point.y_m)) for point in terrain.points]

    if terrain.width_m is not None and terrain.length_m is not None:
        width, length = float(terrain.width_m), float(terrain.length_m)
        return [(0.0, 0.0), (width, 0.0), (width, length), (0.0, length)]

    return None


def is_rectangular(terrain: Terrain) -> bool:
    return len(terrain.points) < 3


def setback_for(width: float, length: float) -> float:
    return min(DEFAULT_SETBACK_M, min(width, length) / 4)


def build_volume(plan: Plan, lot: Lot, base: float) -> StructureRoom:
    origin_x, width, length = lot
    setback = setback_for(width, length)

    return StructureRoom(
        kind="volume",
        id=plan.id,
        plan_id=plan.id,
        plan_title=plan.title,
        name=plan.title,
        level=plan.level,
        x_m=origin_x + width / 2,
        y_m=length / 2,
        base_m=base,
        width_m=width - 2 * setback,
        depth_m=length - 2 * setback,
        height_m=STOREY_HEIGHT_M,
    )


def build_room(plan: Plan, room: Room, base: float) -> StructureRoom:
    width, depth = float(room.width_m), float(room.depth_m)

    return StructureRoom(
        kind="room",
        id=room.id,
        plan_id=plan.id,
        plan_title=plan.title,
        name=room.name,
        level=plan.level,
        x_m=float(room.x_m) + width / 2,
        y_m=float(room.y_m) + depth / 2,
        base_m=base,
        width_m=width,
        depth_m=depth,
        height_m=float(room.height_m),
    )


class StructureService(ProjectScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.terrains = TerrainRepository(session)
        self.plans = PlanRepository(session)
        self.rooms = RoomRepository(session)

    def build(self, project_id: int) -> StructureRead:
        self._ensure_project_exists(project_id)

        terrains, lot = self._place_terrains(project_id)

        return StructureRead(
            project_id=project_id,
            terrains=terrains,
            rooms=self._stack_levels(project_id, lot),
        )

    def _place_terrains(self, project_id: int) -> tuple[list[StructureTerrain], Lot | None]:
        placed: list[StructureTerrain] = []
        lot: Lot | None = None
        cursor_x = 0.0

        for terrain in self.terrains.list_by_project(project_id):
            outline = terrain_outline(terrain)

            if outline is None:
                continue

            min_x = min(x for x, _ in outline)
            min_y = min(y for _, y in outline)
            width = max(x for x, _ in outline) - min_x
            length = max(y for _, y in outline) - min_y

            placed.append(
                StructureTerrain(
                    id=terrain.id,
                    name=terrain.name,
                    outline=[
                        TerrainPointData(x_m=x - min_x + cursor_x, y_m=y - min_y)
                        for x, y in outline
                    ],
                )
            )

            if lot is None and is_rectangular(terrain):
                lot = (cursor_x, width, length)

            cursor_x += width + TERRAIN_GAP_M

        return placed, lot

    def _stack_levels(self, project_id: int, lot: Lot | None) -> list[StructureRoom]:
        rooms_by_plan: dict[int, list[Room]] = {}

        for room in self.rooms.list_by_project(project_id):
            rooms_by_plan.setdefault(room.plan_id, []).append(room)

        stacked: list[StructureRoom] = []
        base = 0.0

        for plan in self.plans.list_by_project(project_id):
            own = rooms_by_plan.get(plan.id, [])
            height = STOREY_HEIGHT_M

            if own:
                stacked.extend(build_room(plan, room, base) for room in own)
                height = max(float(room.height_m) for room in own)
            elif lot is not None:
                stacked.append(build_volume(plan, lot, base))

            base += height

        return stacked
