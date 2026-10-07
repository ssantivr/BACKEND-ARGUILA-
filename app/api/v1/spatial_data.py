from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import require
from app.database import get_session
from app.dtos import (
    Layer,
    SceneFormat,
    SpatialDataRead,
    SpatialElementCreate,
    SpatialElementRead,
    SpatialElementUpdate,
    SpatialImportRead,
    SpatialImportRequest,
    WorkStatus,
)
from app.errors import InvalidDataError
from app.models import User
from app.providers import PROVIDERS
from app.repositories.spatial_element_repository import Footprint
from app.services.scene_service import SceneService
from app.services.spatial_service import SpatialService

router = APIRouter(prefix="/spatial-data", tags=["spatial data"])


def reader(
    session: Session = Depends(get_session),
    user: User = Depends(require("spatial:read")),
) -> SpatialService:
    return SpatialService(session, user)


def writer(
    session: Session = Depends(get_session),
    user: User = Depends(require("spatial:write")),
) -> SpatialService:
    return SpatialService(session, user)


def parse_footprint(bbox: str | None = None) -> Footprint | None:
    if bbox is None:
        return None

    try:
        min_x, min_y, max_x, max_y = (float(part) for part in bbox.split(","))
    except ValueError:
        raise InvalidDataError(
            "bbox debe tener cuatro números separados por comas: min_x,min_y,max_x,max_y."
        ) from None

    if max_x < min_x or max_y < min_y:
        raise InvalidDataError("En bbox, los máximos no pueden ser menores que los mínimos.")

    return min_x, min_y, max_x, max_y


@router.get("", response_model=SpatialDataRead)
def read_spatial_data(
    project_id: int,
    layer: Layer | None = None,
    room_id: int | None = None,
    work_status: WorkStatus | None = None,
    footprint: Footprint | None = Depends(parse_footprint),
    service: SpatialService = Depends(reader),
):
    return service.read(project_id, layer, room_id, work_status, footprint)


@router.get("/scene")
def get_project_scene(
    project_id: int,
    format: SceneFormat = "gltf",
    session: Session = Depends(get_session),
    user: User = Depends(require("spatial:read")),
):
    scene = SceneService(session, user).project_scene(project_id, format)

    return JSONResponse(scene.render(), media_type=scene.media_type)


@router.get("/providers", response_model=list[str])
def list_providers(_: User = Depends(require("spatial:read"))):
    return sorted(PROVIDERS)


@router.post("/import", response_model=SpatialImportRead)
def import_document(data: SpatialImportRequest, service: SpatialService = Depends(writer)):
    return service.import_document(data)


@router.post("/elements", response_model=SpatialElementRead, status_code=status.HTTP_201_CREATED)
def create_element(data: SpatialElementCreate, service: SpatialService = Depends(writer)):
    return service.create(data)


@router.get("/elements/{element_id}", response_model=SpatialElementRead)
def get_element(element_id: int, service: SpatialService = Depends(reader)):
    return service.get(element_id)


@router.patch("/elements/{element_id}", response_model=SpatialElementRead)
def update_element(
    element_id: int,
    data: SpatialElementUpdate,
    service: SpatialService = Depends(writer),
):
    return service.update(element_id, data)


@router.delete("/elements/{element_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_element(element_id: int, service: SpatialService = Depends(writer)):
    service.delete(element_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
