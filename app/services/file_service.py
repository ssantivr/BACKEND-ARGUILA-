from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO

from sqlalchemy.orm import Session

from app import storage
from app.errors import NotFoundError
from app.models import File, User
from app.repositories.file_repository import FileRepository
from app.services.base import ProjectScopedService


def clean_filename(filename: str | None) -> str:
    name = PureWindowsPath(PurePosixPath(filename or "").name).name.strip()
    return name[:255] or "file"


class FileService(ProjectScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.files = FileRepository(session)

    def create(self, project_id: int, filename: str | None, stream: BinaryIO) -> File:
        self._ensure_project_exists(project_id)

        stored_name, mime_type, size = storage.store(stream)

        try:
            return self.files.save(
                File(
                    project_id=project_id,
                    filename=clean_filename(filename),
                    storage_path=stored_name,
                    mime_type=mime_type,
                    size_bytes=size,
                )
            )
        except BaseException:
            storage.remove(stored_name)
            raise

    def list(self, project_id: int) -> list[File]:
        self._ensure_project_exists(project_id)

        return self.files.list_by_project(project_id)

    def get(self, file_id: int) -> File:
        file = self.files.get(file_id)

        if file is None or not self._owns(file.project_id):
            raise NotFoundError("File not found")

        return file

    def content_path(self, file: File) -> Path:
        path = storage.path_for(file.storage_path)

        if not path.is_file():
            raise NotFoundError("File content is missing from storage")

        return path

    def delete(self, file_id: int) -> None:
        file = self.get(file_id)
        stored_name = file.storage_path

        self.files.delete(file)
        storage.remove(stored_name)
