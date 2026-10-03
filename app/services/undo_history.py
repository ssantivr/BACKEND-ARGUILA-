from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.data_structures import DoublyLinkedList
from app.database import Base

MAX_ENTRIES_PER_PROJECT = 20


@dataclass(frozen=True)
class DeletedRecord:
    project_id: int
    kind: str
    label: str
    model: type[Base]
    values: dict[str, Any]


def snapshot(kind: str, label: str, instance: Base) -> DeletedRecord:
    values = {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
        if not column.primary_key
    }

    return DeletedRecord(
        project_id=values["project_id"],
        kind=kind,
        label=label,
        model=type(instance),
        values=values,
    )


class UndoHistory:
    def __init__(self, capacity: int = MAX_ENTRIES_PER_PROJECT) -> None:
        self._capacity = capacity
        self._by_project: dict[int, DoublyLinkedList[DeletedRecord]] = {}
        self._lock = Lock()

    def record(self, deleted: DeletedRecord) -> None:
        with self._lock:
            entries = self._by_project.setdefault(
                deleted.project_id, DoublyLinkedList()
            )
            entries.push_back(deleted)

            if len(entries) > self._capacity:
                entries.pop_front()

    def pop_last(self, project_id: int) -> DeletedRecord | None:
        with self._lock:
            entries = self._by_project.get(project_id)

            if entries is None or entries.is_empty():
                return None

            return entries.pop_back()

    def list(self, project_id: int) -> list[DeletedRecord]:
        with self._lock:
            entries = self._by_project.get(project_id)
            return [] if entries is None else list(reversed(entries))

    def forget(self, project_id: int) -> None:
        with self._lock:
            self._by_project.pop(project_id, None)

    def clear(self) -> None:
        with self._lock:
            self._by_project.clear()


undo_history = UndoHistory()
