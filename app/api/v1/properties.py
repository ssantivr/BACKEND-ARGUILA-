from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require
from app.database import get_session
from app.dtos import PropertyCreate, PropertyRead, PropertyUpdate
from app.models import User
from app.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["properties"])


def reader(
    session: Session = Depends(get_session),
    user: User = Depends(require("units:read")),
) -> PropertyService:
    return PropertyService(session, user)


def writer(
    session: Session = Depends(get_session),
    user: User = Depends(require("units:write")),
) -> PropertyService:
    return PropertyService(session, user)


@router.get("", response_model=list[PropertyRead])
def list_properties(project_id: int | None = None, service: PropertyService = Depends(reader)):
    return service.list(project_id)


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
def create_property(data: PropertyCreate, service: PropertyService = Depends(writer)):
    return service.create(data)


@router.get("/{property_id}", response_model=PropertyRead)
def get_property(property_id: int, service: PropertyService = Depends(reader)):
    return service.get(property_id)


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: int,
    data: PropertyUpdate,
    service: PropertyService = Depends(writer),
):
    return service.update(property_id, data)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(property_id: int, service: PropertyService = Depends(writer)):
    service.delete(property_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
