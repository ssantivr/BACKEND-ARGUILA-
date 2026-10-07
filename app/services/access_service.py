from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository

DEFAULT_ROLE = "architect"


def permissions_of(user: User) -> set[str]:
    return {permission.code for role in user.roles for permission in role.permissions}


class AccessService:
    def __init__(self, session: Session) -> None:
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)

    def assign_roles(self, user_id: int, names: list[str]) -> User:
        user = self.users.get(user_id)

        if user is None:
            raise NotFoundError("Usuario no encontrado.")

        user.roles = self.roles.list_by_names(names)

        return self.users.save(user)
