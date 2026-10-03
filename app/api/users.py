from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(session)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, service: UserService = Depends(get_service)):
    return service.create(data)


@router.get("", response_model=list[UserRead])
def list_users(service: UserService = Depends(get_service)):
    return service.list()


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, service: UserService = Depends(get_service)):
    return service.get(user_id)
