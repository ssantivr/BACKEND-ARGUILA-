from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, project_id: int) -> Project | None:
        return self.session.get(Project, project_id)

    def get_by_owner_and_name(self, owner_id: int, name: str) -> Project | None:
        return self.session.scalar(
            select(Project).where(Project.owner_id == owner_id, Project.name == name)
        )

    def list(
        self,
        owner_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[Project]:
        query = select(Project).order_by(Project.id)

        if owner_id is not None:
            query = query.where(Project.owner_id == owner_id)

        if status is not None:
            query = query.where(Project.status == status)

        if search:
            query = query.where(Project.name.icontains(search, autoescape=True))

        return list(self.session.scalars(query))

    def save(self, project: Project) -> Project:
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        self.session.delete(project)
        self.session.commit()
