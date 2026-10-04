from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Room


class RoomRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, room_id: int) -> Room | None:
        return self.session.get(Room, room_id)

    def list_by_project(self, project_id: int) -> list[Room]:
        query = select(Room).where(Room.project_id == project_id)
        return list(self.session.scalars(query.order_by(Room.id)))

    def save(self, room: Room) -> Room:
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        return room

    def delete(self, room: Room) -> None:
        self.session.delete(room)
        self.session.commit()
