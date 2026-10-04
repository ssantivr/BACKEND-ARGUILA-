from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StructuralComponent


class ComponentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, component_id: int) -> StructuralComponent | None:
        return self.session.get(StructuralComponent, component_id)

    def list_by_project(
        self, project_id: int, kind: str | None = None
    ) -> list[StructuralComponent]:
        query = select(StructuralComponent).where(StructuralComponent.project_id == project_id)

        if kind is not None:
            query = query.where(StructuralComponent.kind == kind)

        return list(self.session.scalars(query.order_by(StructuralComponent.id)))

    def save(self, component: StructuralComponent) -> StructuralComponent:
        self.session.add(component)
        self.session.commit()
        self.session.refresh(component)
        return component

    def delete(self, component: StructuralComponent) -> None:
        self.session.delete(component)
        self.session.commit()
