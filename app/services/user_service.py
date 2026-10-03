from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas import UserCreate


class UserService:
    def __init__(self, session: Session) -> None:
        self.users = UserRepository(session)

    def create(self, data: UserCreate) -> User:
        if self.users.get_by_email(data.email) is not None:
            raise ConflictError("Email is already registered")

        return self.users.add(User(name=data.name, email=data.email))

    def list(self) -> list[User]:
        return self.users.list()

    def get(self, user_id: int) -> User:
        user = self.users.get(user_id)

        if user is None:
            raise NotFoundError("User not found")

        return user
