from fastapi import APIRouter, Depends, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import FileRead
from app.services.file_service import FileService

router = APIRouter(tags=["files"])


def get_service(session: Session = Depends(get_session)) -> FileService:
    return FileService(session)


@router.post(
    "/projects/{project_id}/files",
    response_model=FileRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_file(
    project_id: int,
    file: UploadFile,
    service: FileService = Depends(get_service),
):
    return service.create(project_id, file.filename, file.file)


@router.get("/projects/{project_id}/files", response_model=list[FileRead])
def list_files(project_id: int, service: FileService = Depends(get_service)):
    return service.list(project_id)


@router.get("/files/{file_id}", response_model=FileRead)
def get_file(file_id: int, service: FileService = Depends(get_service)):
    return service.get(file_id)


@router.get("/files/{file_id}/content")
def get_file_content(file_id: int, service: FileService = Depends(get_service)):
    file = service.get(file_id)

    return FileResponse(
        service.content_path(file),
        media_type=file.mime_type,
        filename=file.filename,
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: int, service: FileService = Depends(get_service)):
    service.delete(file_id)
    return Response(status_code=204)
