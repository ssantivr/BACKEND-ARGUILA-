from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Material


class MaterialRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, material_id: int) -> Material | None:
        return self.session.get(Material, material_id)

    def get_by_project_and_name(self, project_id: int, name: str) -> Material | None:
        return self.session.scalar(
            select(Material).where(Material.project_id == project_id, Material.name == name)
        )

    def list_by_project(self, project_id: int, category: str | None = None) -> list[Material]:
        query = select(Material).where(Material.project_id == project_id)

        if category is not None:
            query = query.where(Material.category == category)

        return list(self.session.scalars(query.order_by(Material.id)))

    def save(self, material: Material) -> Material:
        self.session.add(material)
        self.session.commit()
        self.session.refresh(material)
        return material

    def delete(self, material: Material) -> None:
        self.session.delete(material)
        self.session.commit()
