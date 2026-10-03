from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Material
from app.repositories.material_repository import MaterialRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas import MaterialCreate, MaterialUpdate
from app.services.undo_history import snapshot, undo_history


class MaterialService:
    def __init__(self, session: Session) -> None:
        self.materials = MaterialRepository(session)
        self.projects = ProjectRepository(session)

    def create(self, project_id: int, data: MaterialCreate) -> Material:
        self._ensure_project_exists(project_id)
        self._ensure_name_is_free(project_id, data.name)

        return self.materials.save(
            Material(project_id=project_id, **data.model_dump())
        )

    def list(self, project_id: int, category: str | None = None) -> list[Material]:
        self._ensure_project_exists(project_id)

        return self.materials.list_by_project(project_id, category=category)

    def get(self, material_id: int) -> Material:
        material = self.materials.get(material_id)

        if material is None:
            raise NotFoundError("Material not found")

        return material

    def update(self, material_id: int, data: MaterialUpdate) -> Material:
        material = self.get(material_id)
        changes = data.model_dump(exclude_unset=True)

        # these columns are NOT NULL: an explicit null means "leave unchanged"
        for required in ("name", "unit", "quantity", "unit_cost"):
            if changes.get(required, "") is None:
                del changes[required]

        if "name" in changes and changes["name"] != material.name:
            self._ensure_name_is_free(material.project_id, changes["name"])

        for field, value in changes.items():
            setattr(material, field, value)

        return self.materials.save(material)

    def delete(self, material_id: int) -> None:
        material = self.get(material_id)
        deleted = snapshot("material", material.name, material)
        self.materials.delete(material)
        undo_history.record(deleted)

    def _ensure_project_exists(self, project_id: int) -> None:
        if self.projects.get(project_id) is None:
            raise NotFoundError("Project not found")

    def _ensure_name_is_free(self, project_id: int, name: str) -> None:
        if self.materials.get_by_project_and_name(project_id, name) is not None:
            raise ConflictError("Project already has a material with this name")
