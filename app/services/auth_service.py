from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import security
from app.errors import AuthenticationError, ConflictError
from app.models import User, UserSession
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas import LoginRequest, RegisterRequest

SESSION_LIFETIME = timedelta(days=7)


def _now() -> datetime:
    # Stored as naive UTC, matching the TIMESTAMP columns.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, session: Session) -> None:
        self.users = UserRepository(session)
        self.sessions = SessionRepository(session)

    def register(self, data: RegisterRequest) -> tuple[User, str]:
        email = normalize_email(data.email)

        if self.users.get_by_email(email) is not None:
            raise ConflictError("Email is already registered")

        user = self.users.add(
            User(
                name=data.name.strip(),
                email=email,
                password_hash=security.hash_password(data.password),
            )
        )

        return user, self._start_session(user)

    def login(self, data: LoginRequest) -> tuple[User, str]:
        user = self.users.get_by_email(normalize_email(data.email))
        stored = user.password_hash if user else security.DUMMY_PASSWORD_HASH

        if not security.verify_password(data.password, stored) or user is None:
            raise AuthenticationError("Invalid email or password")

        return user, self._start_session(user)

    def logout(self, token: str | None) -> None:
        if token:
            self.sessions.delete_by_token_hash(security.hash_session_token(token))

    def user_for_token(self, token: str | None) -> User:
        if not token:
            raise AuthenticationError("Not authenticated")

        user_session = self.sessions.get_by_token_hash(
            security.hash_session_token(token)
        )

        if user_session is None or user_session.expires_at <= _now():
            raise AuthenticationError("Not authenticated")

        user = self.users.get(user_session.user_id)

        if user is None:
            raise AuthenticationError("Not authenticated")

        return user

    def _start_session(self, user: User) -> str:
        now = _now()
        self.sessions.delete_expired(now)

        token = security.new_session_token()
        self.sessions.add(
            UserSession(
                user_id=user.id,
                token_hash=security.hash_session_token(token),
                expires_at=now + SESSION_LIFETIME,
            )
        )

        return token
