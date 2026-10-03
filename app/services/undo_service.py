from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import File
from app.services.base import ProjectScopedService
from app.services.undo_history import DeletedRecord, undo_history


class UndoService(ProjectScopedService):
    def list(self, project_id: int) -> list[DeletedRecord]:
        self._ensure_project_exists(project_id)

        return undo_history.list(project_id)

    def undo_last(self, project_id: int) -> DeletedRecord:
        self._ensure_project_exists(project_id)

        deleted = undo_history.pop_last(project_id)

        if deleted is None:
            raise NotFoundError("Nothing to undo")

        values = dict(deleted.values)

        if values.get("file_id") is not None and (
            self.session.get(File, values["file_id"]) is None
        ):
            values["file_id"] = None

        try:
            self.session.add(deleted.model(**values))
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            undo_history.record(deleted)
            raise ConflictError(
                f'Cannot restore "{deleted.label}": it conflicts with existing data'
            ) from None

        return deleted
