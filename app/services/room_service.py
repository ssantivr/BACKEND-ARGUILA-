from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Room, User
from app.repositories.plan_repository import PlanRepository
from app.repositories.room_repository import RoomRepository
from app.schemas import RoomCreate, RoomUpdate
from app.services.base import ProjectScopedService
from app.services.undo_history import snapshot, undo_history


class RoomService(ProjectScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.rooms = RoomRepository(session)
        self.plans = PlanRepository(session)

    def create(self, project_id: int, data: RoomCreate) -> Room:
        self._ensure_project_exists(project_id)
        self._ensure_plan_in_project(data.plan_id, project_id)

        return self.rooms.save(Room(project_id=project_id, **data.model_dump()))

    def list(self, project_id: int) -> list[Room]:
        self._ensure_project_exists(project_id)

        return self.rooms.list_by_project(project_id)

    def get(self, room_id: int) -> Room:
        room = self.rooms.get(room_id)

        if room is None or not self._owns(room.project_id):
            raise NotFoundError("Room not found")

        return room

    def update(self, room_id: int, data: RoomUpdate) -> Room:
        room = self.get(room_id)
        changes = {
            field: value
            for field, value in data.model_dump(exclude_unset=True).items()
            if value is not None
        }

        if "plan_id" in changes:
            self._ensure_plan_in_project(changes["plan_id"], room.project_id)

        for field, value in changes.items():
            setattr(room, field, value)

        return self.rooms.save(room)

    def delete(self, room_id: int) -> None:
        room = self.get(room_id)
        deleted = snapshot("room", room.name, room)
        self.rooms.delete(room)
        undo_history.record(deleted, session=self.session)

    def _ensure_plan_in_project(self, plan_id: int, project_id: int) -> None:
        plan = self.plans.get(plan_id)

        if plan is None or plan.project_id != project_id:
            raise NotFoundError("Plan not found in this project")
