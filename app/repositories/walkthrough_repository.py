from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import RenovationLog, WalkthroughStep


class WalkthroughStepRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, step_id: int) -> WalkthroughStep | None:
        return self.session.get(WalkthroughStep, step_id)

    def list_by_project(self, project_id: int) -> list[WalkthroughStep]:
        query = select(WalkthroughStep).where(WalkthroughStep.project_id == project_id)
        return list(
            self.session.scalars(query.order_by(WalkthroughStep.position, WalkthroughStep.id))
        )

    def next_position(self, project_id: int) -> int:
        last = self.session.scalar(
            select(func.max(WalkthroughStep.position)).where(
                WalkthroughStep.project_id == project_id
            )
        )

        return 0 if last is None else last + 1

    def save(self, step: WalkthroughStep) -> WalkthroughStep:
        self.session.add(step)
        self.session.commit()
        self.session.refresh(step)
        return step

    def delete(self, step: WalkthroughStep) -> None:
        self.session.delete(step)
        self.session.commit()


class RenovationLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, log_id: int) -> RenovationLog | None:
        return self.session.get(RenovationLog, log_id)

    def list_by_project(
        self,
        project_id: int,
        room_id: int | None = None,
        status: str | None = None,
    ) -> list[RenovationLog]:
        query = select(RenovationLog).where(RenovationLog.project_id == project_id)

        if room_id is not None:
            query = query.where(RenovationLog.room_id == room_id)

        if status is not None:
            query = query.where(RenovationLog.status == status)

        return list(
            self.session.scalars(
                query.order_by(RenovationLog.planned_start.nulls_last(), RenovationLog.id)
            )
        )

    def save(self, log: RenovationLog) -> RenovationLog:
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def delete(self, log: RenovationLog) -> None:
        self.session.delete(log)
        self.session.commit()
