from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require
from app.database import get_session
from app.dtos import UnitCreate, UnitRead, UnitStatus, UnitUpdate
from app.models import User
from app.services.property_service import UnitService

router = APIRouter(prefix="/units", tags=["units"])


def reader(
    session: Session = Depends(get_session),
    user: User = Depends(require("units:read")),
) -> UnitService:
    return UnitService(session, user)


def writer(
    session: Session = Depends(get_session),
    user: User = Depends(require("units:write")),
) -> UnitService:
    return UnitService(session, user)


@router.get("", response_model=list[UnitRead])
def list_units(
    project_id: int | None = None,
    property_id: int | None = None,
    status: UnitStatus | None = None,
    service: UnitService = Depends(reader),
):
    return service.list(project_id, property_id, status)


@router.post("", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
def create_unit(data: UnitCreate, service: UnitService = Depends(writer)):
    return service.create(data)


@router.get("/{unit_id}", response_model=UnitRead)
def get_unit(unit_id: int, service: UnitService = Depends(reader)):
    return service.get(unit_id)


@router.patch("/{unit_id}", response_model=UnitRead)
def update_unit(unit_id: int, data: UnitUpdate, service: UnitService = Depends(writer)):
    return service.update(unit_id, data)


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(unit_id: int, service: UnitService = Depends(writer)):
    service.delete(unit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
