import os
import smtplib
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import security
from app.errors import (
    AuthenticationError,
    ConflictError,
    InvalidTokenError,
    TooManyAttemptsError,
)
from app.logs import logger
from app.mailer import Mailer
from app.models import PasswordResetToken, User, UserSession
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas import LoginRequest, RegisterRequest
from app.services.login_limiter import login_limiter, reset_request_limiter

SESSION_LIFETIME = timedelta(days=7)
RESET_TOKEN_LIFETIME = timedelta(minutes=30)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, session: Session) -> None:
        self.users = UserRepository(session)
        self.sessions = SessionRepository(session)
        self.resets = PasswordResetRepository(session)

    def register(self, data: RegisterRequest) -> tuple[User, str]:
        email = normalize_email(data.email)

        if self.users.get_by_email(email) is not None:
            raise ConflictError("Email is already registered")

        try:
            user = self.users.add(
                User(
                    name=data.name.strip(),
                    email=email,
                    password_hash=security.hash_password(data.password),
                )
            )
        except IntegrityError:
            self.users.session.rollback()
            raise ConflictError("Email is already registered") from None

        return user, self._start_session(user)

    def login(self, data: LoginRequest) -> tuple[User, str]:
        email = normalize_email(data.email)

        if login_limiter.is_blocked(email, self.users.session):
            logger.warning("login_blocked")
            raise TooManyAttemptsError("Too many failed attempts, try again in a minute")

        user = self.users.get_by_email(email)
        stored = user.password_hash if user else security.DUMMY_PASSWORD_HASH

        if not security.verify_password(data.password, stored) or user is None:
            login_limiter.record_failure(email, self.users.session)
            logger.warning("login_failed")
            raise AuthenticationError("Invalid email or password")

        login_limiter.reset(email, self.users.session)

        if security.needs_rehash(user.password_hash):
            user.password_hash = security.hash_password(data.password)
            self.users.save(user)
            logger.info("password_rehashed", extra={"user_id": user.id})

        return user, self._start_session(user)

    def request_password_reset(self, email: str, mailer: Mailer) -> None:
        email = normalize_email(email)

        if reset_request_limiter.is_blocked(email, self.users.session):
            return

        reset_request_limiter.record_failure(email, self.users.session)
        user = self.users.get_by_email(email)

        if user is None:
            return

        now = _now()
        self.resets.delete_expired(now)
        self.resets.delete_for_user(user.id)

        token = security.new_session_token()
        self.resets.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=security.hash_session_token(token),
                expires_at=now + RESET_TOKEN_LIFETIME,
            )
        )

        app_url = os.environ.get("APP_URL", "http://localhost:5173").rstrip("/")

        try:
            mailer.send(
                user.email,
                "Restablecer tu contraseña de ARQUILA",
                "Para elegir una contraseña nueva abre este enlace, válido durante 30 minutos:\n\n"
                f"{app_url}/?reset_token={token}\n\n"
                "Si no lo pediste, ignora este mensaje.",
            )
        except (smtplib.SMTPException, OSError):
            logger.exception("password_reset_mail_failed", extra={"user_id": user.id})

    def reset_password(self, token: str, password: str) -> None:
        reset = self.resets.get_by_token_hash(security.hash_session_token(token))

        if reset is None or reset.expires_at <= _now():
            raise InvalidTokenError("The reset link is invalid or has expired")

        user = self.users.get(reset.user_id)

        if user is None:
            raise InvalidTokenError("The reset link is invalid or has expired")

        user.password_hash = security.hash_password(password)
        self.users.save(user)
        self.resets.delete_for_user(user.id)
        self.sessions.delete_for_user(user.id)
        login_limiter.reset(user.email, self.users.session)

    def logout(self, token: str | None) -> None:
        if token:
            self.sessions.delete_by_token_hash(security.hash_session_token(token))

    def user_for_token(self, token: str | None) -> User:
        if not token:
            raise AuthenticationError("Not authenticated")

        user_session = self.sessions.get_by_token_hash(security.hash_session_token(token))

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
