from __future__ import annotations  # the `list` method shadows the builtin below

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.repositories.project_repository import ProjectRepository
from app.services.undo_history import DeletedRecord, undo_history


class UndoService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.projects = ProjectRepository(session)

    def list(self, project_id: int) -> list[DeletedRecord]:
        self._ensure_project_exists(project_id)

        return undo_history.list(project_id)

    def undo_last(self, project_id: int) -> DeletedRecord:
        self._ensure_project_exists(project_id)

        deleted = undo_history.pop_last(project_id)

        if deleted is None:
            raise NotFoundError("Nothing to undo")

        try:
            self.session.add(deleted.model(**deleted.values))
            self.session.commit()
        except IntegrityError:
            # e.g. a material with the same name was created after the deletion.
            self.session.rollback()
            undo_history.record(deleted)
            raise ConflictError(
                f'Cannot restore "{deleted.label}": it conflicts with existing data'
            ) from None

        return deleted

    def _ensure_project_exists(self, project_id: int) -> None:
        if self.projects.get(project_id) is None:
            raise NotFoundError("Project not found")
