from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import User
from app.services.auth_service import AuthService

SESSION_COOKIE = "arquila_session"


def get_current_user(
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    session: Session = Depends(get_session),
) -> User:
    """Resolves the session cookie to a user, or fails with 401."""
    return AuthService(session).user_for_token(token)
