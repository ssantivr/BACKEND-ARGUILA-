from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Plan


class PlanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, plan_id: int) -> Plan | None:
        return self.session.get(Plan, plan_id)

    def list_by_project(self, project_id: int) -> list[Plan]:
        query = select(Plan).where(Plan.project_id == project_id)
        return list(self.session.scalars(query.order_by(Plan.id)))

    def save(self, plan: Plan) -> Plan:
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan

    def delete(self, plan: Plan) -> None:
        self.session.delete(plan)
        self.session.commit()
