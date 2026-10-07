from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Room, User
from app.repositories.spatial_element_repository import SpatialElementRepository
from app.scenes import ENCODERS, ProjectScene, RoomScene, Scene
from app.services.base import ApiScopedService
from app.services.structure_service import StructureService


class SceneService(ApiScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.elements = SpatialElementRepository(session)
        self.structure = StructureService(session, user)

    def room_scene(self, room_id: int, output: str) -> Scene:
        stored = self.session.get(Room, room_id)

        if stored is None or not self._owns(stored.project_id):
            raise NotFoundError("Cuarto no encontrado.")

        placed = next(
            room
            for room in self.structure.build(stored.project_id).rooms
            if room.kind == "room" and room.id == room_id
        )

        return RoomScene(
            ENCODERS[output],
            placed,
            self.elements.list_by_project(stored.project_id, room_id=room_id),
        )

    def project_scene(self, project_id: int, output: str) -> Scene:
        self._require_project(project_id)

        project = self.projects.get(project_id)

        return ProjectScene(
            ENCODERS[output],
            project.name,
            [room for room in self.structure.build(project_id).rooms if room.kind == "room"],
            self.elements.list_by_project(project_id),
        )
