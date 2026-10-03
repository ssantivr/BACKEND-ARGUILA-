from __future__ import annotations  # the `list` method shadows the builtin below

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Recommendation
from app.repositories.material_repository import MaterialRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.terrain_repository import TerrainRepository
from app.schemas import RecommendationCreate
from app.services import recommendation_rules


class RecommendationService:
    def __init__(self, session: Session) -> None:
        self.recommendations = RecommendationRepository(session)
        self.projects = ProjectRepository(session)
        self.terrains = TerrainRepository(session)
        self.materials = MaterialRepository(session)

    def create(self, project_id: int, data: RecommendationCreate) -> Recommendation:
        self._ensure_project_exists(project_id)

        return self.recommendations.save(
            Recommendation(project_id=project_id, source="user", **data.model_dump())
        )

    def list(
        self,
        project_id: int,
        category: str | None = None,
        source: str | None = None,
    ) -> list[Recommendation]:
        self._ensure_project_exists(project_id)

        return self.recommendations.list_by_project(
            project_id, category=category, source=source
        )

    def generate(self, project_id: int) -> list[Recommendation]:
        """Re-evaluates the rules and replaces the previous system recommendations.

        Recommendations written by users are never touched.
        """
        self._ensure_project_exists(project_id)

        suggestions = recommendation_rules.evaluate(
            self.terrains.list_by_project(project_id),
            self.materials.list_by_project(project_id),
        )

        return self.recommendations.replace_by_source(
            project_id,
            "system",
            [
                Recommendation(
                    project_id=project_id,
                    source="system",
                    category=category,
                    content=content,
                )
                for category, content in suggestions
            ],
        )

    def delete(self, recommendation_id: int) -> None:
        recommendation = self.recommendations.get(recommendation_id)

        if recommendation is None:
            raise NotFoundError("Recommendation not found")

        self.recommendations.delete(recommendation)

    def _ensure_project_exists(self, project_id: int) -> None:
        if self.projects.get(project_id) is None:
            raise NotFoundError("Project not found")
