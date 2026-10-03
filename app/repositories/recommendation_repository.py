from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Recommendation


class RecommendationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, recommendation_id: int) -> Recommendation | None:
        return self.session.get(Recommendation, recommendation_id)

    def list_by_project(
        self,
        project_id: int,
        category: str | None = None,
        source: str | None = None,
    ) -> list[Recommendation]:
        query = select(Recommendation).where(Recommendation.project_id == project_id)

        if category is not None:
            query = query.where(Recommendation.category == category)

        if source is not None:
            query = query.where(Recommendation.source == source)

        return list(self.session.scalars(query.order_by(Recommendation.id)))

    def save(self, recommendation: Recommendation) -> Recommendation:
        self.session.add(recommendation)
        self.session.commit()
        self.session.refresh(recommendation)
        return recommendation

    def replace_by_source(
        self, project_id: int, source: str, recommendations: list[Recommendation]
    ) -> list[Recommendation]:
        """Swaps all of a project's recommendations from one source atomically."""
        self.session.execute(
            delete(Recommendation).where(
                Recommendation.project_id == project_id,
                Recommendation.source == source,
            )
        )
        self.session.add_all(recommendations)
        self.session.commit()

        return self.list_by_project(project_id, source=source)

    def delete(self, recommendation: Recommendation) -> None:
        self.session.delete(recommendation)
        self.session.commit()
