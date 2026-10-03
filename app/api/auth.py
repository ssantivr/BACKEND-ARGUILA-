import os

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, get_current_user
from app.database import get_session
from app.models import User
from app.mailer import Mailer, get_mailer
from app.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    UserRead,
)
from app.services.auth_service import SESSION_LIFETIME, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=os.environ.get("COOKIE_SECURE", "0") == "1",
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    response: Response,
    service: AuthService = Depends(get_service),
):
    user, token = service.register(data)
    set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserRead)
def login(
    data: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_service),
):
    user, token = service.login(data)
    set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=204)
def logout(
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    service: AuthService = Depends(get_service),
):
    service.logout(token)

    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.post("/password-reset", status_code=204)
def request_password_reset(
    data: PasswordResetRequest,
    service: AuthService = Depends(get_service),
    mailer: Mailer = Depends(get_mailer),
):
    service.request_password_reset(data.email, mailer)
    return Response(status_code=204)


@router.post("/password-reset/confirm", status_code=204)
def confirm_password_reset(
    data: PasswordResetConfirm,
    service: AuthService = Depends(get_service),
):
    service.reset_password(data.token, data.password)

    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
