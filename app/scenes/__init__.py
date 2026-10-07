from abc import ABC, abstractmethod
from typing import Any

from app.models import SpatialElement
from app.scenes.encoders import ENCODERS, ROOM_LAYER, Box, SceneEncoder
from app.schemas import StructureRoom

__all__ = ["ENCODERS", "ProjectScene", "RoomScene", "Scene"]


def room_box(room: StructureRoom) -> Box:
    half_width, half_depth = room.width_m / 2, room.depth_m / 2

    return Box(
        name=room.name,
        layer=ROOM_LAYER,
        kind=room.kind,
        minimum=(room.x_m - half_width, room.y_m - half_depth, room.base_m),
        maximum=(room.x_m + half_width, room.y_m + half_depth, room.base_m + room.height_m),
    )


def element_box(element: SpatialElement) -> Box:
    return Box(
        name=element.name,
        layer=element.layer,
        kind=element.kind,
        minimum=(float(element.min_x_m), float(element.min_y_m), float(element.min_z_m)),
        maximum=(float(element.max_x_m), float(element.max_y_m), float(element.max_z_m)),
    )


class Scene(ABC):
    """Abstraction side of the bridge: what is drawn, independent of the output format.

    The business rules decide which rooms and elements belong to a scene; the encoder it
    is given decides how they are written. Either side can grow without touching the other.
    """

    def __init__(self, encoder: SceneEncoder) -> None:
        self.encoder = encoder

    @abstractmethod
    def title(self) -> str: ...

    @abstractmethod
    def boxes(self) -> list[Box]: ...

    @property
    def media_type(self) -> str:
        return self.encoder.media_type

    def render(self) -> dict[str, Any]:
        return self.encoder.encode(self.title(), self.boxes())


class RoomScene(Scene):
    def __init__(
        self, encoder: SceneEncoder, room: StructureRoom, elements: list[SpatialElement]
    ) -> None:
        super().__init__(encoder)
        self.room = room
        self.elements = elements

    def title(self) -> str:
        return self.room.name

    def boxes(self) -> list[Box]:
        return [room_box(self.room), *map(element_box, self.elements)]


class ProjectScene(Scene):
    def __init__(
        self,
        encoder: SceneEncoder,
        name: str,
        rooms: list[StructureRoom],
        elements: list[SpatialElement],
    ) -> None:
        super().__init__(encoder)
        self.name = name
        self.rooms = rooms
        self.elements = elements

    def title(self) -> str:
        return self.name

    def boxes(self) -> list[Box]:
        return [*map(room_box, self.rooms), *map(element_box, self.elements)]
