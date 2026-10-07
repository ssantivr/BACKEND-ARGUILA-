from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.dtos import (
    RenovationLogCreate,
    RenovationLogUpdate,
    WalkthroughRead,
    WalkthroughStepCreate,
    WalkthroughStepUpdate,
    check_timeline,
)
from app.errors import InvalidDataError, NotFoundError
from app.models import RenovationLog, SpatialElement, User, WalkthroughStep
from app.repositories.walkthrough_repository import (
    RenovationLogRepository,
    WalkthroughStepRepository,
)
from app.services.base import ApiScopedService, changes_in

COMPLETED = "completed"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WalkthroughService(ApiScopedService):
    def __init__(self, session: Session, user: User) -> None:
        super().__init__(session, user)
        self.steps = WalkthroughStepRepository(session)
        self.logs = RenovationLogRepository(session)

    def read(self, project_id: int) -> WalkthroughRead:
        self._require_project(project_id)

        return WalkthroughRead(
            project_id=project_id,
            steps=self.steps.list_by_project(project_id),
            renovation_logs=self.logs.list_by_project(project_id),
        )

    def create_step(self, data: WalkthroughStepCreate) -> WalkthroughStep:
        self._require_project(data.project_id)

        if data.room_id is not None:
            self._require_room(data.room_id, data.project_id)

        values = data.model_dump()

        if values["position"] is None:
            values["position"] = self.steps.next_position(data.project_id)

        return self.steps.save(WalkthroughStep(**values))

    def get_step(self, step_id: int) -> WalkthroughStep:
        step = self.steps.get(step_id)

        if step is None or not self._owns(step.project_id):
            raise NotFoundError("Paso del recorrido no encontrado.")

        return step

    def update_step(self, step_id: int, data: WalkthroughStepUpdate) -> WalkthroughStep:
        step = self.get_step(step_id)
        changes = changes_in(data, nullable={"room_id", "description"})

        if changes.get("room_id") is not None:
            self._require_room(changes["room_id"], step.project_id)

        for field, value in changes.items():
            setattr(step, field, value)

        return self.steps.save(step)

    def delete_step(self, step_id: int) -> None:
        self.steps.delete(self.get_step(step_id))

    def list_logs(
        self,
        project_id: int,
        room_id: int | None = None,
        status: str | None = None,
    ) -> list[RenovationLog]:
        self._require_project(project_id)

        return self.logs.list_by_project(project_id, room_id, status)

    def create_log(self, data: RenovationLogCreate) -> RenovationLog:
        self._require_project(data.project_id)
        self._check_links(data.project_id, data.room_id, data.spatial_element_id)

        log = RenovationLog(**data.model_dump(), created_by=self.user.id)
        self._stamp_completion(log)

        return self.logs.save(log)

    def get_log(self, log_id: int) -> RenovationLog:
        log = self.logs.get(log_id)

        if log is None or not self._owns(log.project_id):
            raise NotFoundError("Registro de obra no encontrado.")

        return log

    def update_log(self, log_id: int, data: RenovationLogUpdate) -> RenovationLog:
        log = self.get_log(log_id)
        changes = changes_in(
            data,
            nullable={
                "room_id",
                "spatial_element_id",
                "description",
                "planned_start",
                "planned_end",
                "estimated_cost",
            },
        )

        self._check_links(log.project_id, changes.get("room_id"), changes.get("spatial_element_id"))

        try:
            check_timeline(
                changes.get("planned_start", log.planned_start),
                changes.get("planned_end", log.planned_end),
            )
        except ValueError as error:
            raise InvalidDataError(str(error)) from None

        for field, value in changes.items():
            setattr(log, field, value)

        self._stamp_completion(log)

        return self.logs.save(log)

    def delete_log(self, log_id: int) -> None:
        self.logs.delete(self.get_log(log_id))

    def _check_links(self, project_id: int, room_id: int | None, element_id: int | None) -> None:
        if room_id is not None:
            self._require_room(room_id, project_id)

        if element_id is not None:
            element = self.session.get(SpatialElement, element_id)

            if element is None or element.project_id != project_id:
                raise NotFoundError("Ese elemento espacial no pertenece a este proyecto.")

    def _stamp_completion(self, log: RenovationLog) -> None:
        if log.status != COMPLETED:
            log.completed_at = None
        elif log.completed_at is None:
            log.completed_at = _now()
