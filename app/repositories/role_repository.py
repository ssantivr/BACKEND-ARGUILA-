from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role


class RoleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_names(self, names: Iterable[str]) -> list[Role]:
        query = select(Role).where(Role.name.in_(set(names)))
        return list(self.session.scalars(query.order_by(Role.id)))
