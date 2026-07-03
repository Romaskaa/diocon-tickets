from uuid import UUID

from sqlalchemy import and_, select

from src.shared.infra.repos import ModelMapper, SqlAlchemyRepository
from src.shared.schemas import Page, Pagination

from ..domain.entities import Feedback
from ..domain.repos import FeedbackFilters
from ..domain.vo import FeedbackRating
from .models import FeedbackOrm


class FeedbackMapper(ModelMapper[Feedback, FeedbackOrm]):
    """
    Маппер между доменной сущностью Feedback и ORM-моделью FeedbackOrm.
    """

    @staticmethod
    def to_entity(model: FeedbackOrm) -> Feedback:
        return Feedback(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            ticket_id=model.ticket_id,
            author_id=model.author_id,
            rating=FeedbackRating(model.rating), 
            comment=model.comment,
        )
    
    @staticmethod
    def from_entity(entity: Feedback) -> FeedbackOrm:
        return FeedbackOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            ticket_id=entity.ticket_id,
            author_id=entity.author_id,
            rating=entity.rating.value,
            comment=entity.comment,
        )
    

class SqlFeedbackRepository(SqlAlchemyRepository[Feedback, FeedbackOrm]):
    """
    SQLAlchemy-репозиторий для отзывов.
    """

    model = FeedbackOrm
    model_mapper = FeedbackMapper

    async def find_by_ticket(self, ticket_id: UUID) -> Feedback | None:
        """
        Получить активный отзыв по тикету.
        """

        stmt = select(self.model).where(
            self.model.ticket_id == ticket_id,
            self.model.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)
    
    async def paginate(
            self,
            pagination: Pagination,
            filters: FeedbackFilters | None = None,
    ) -> Page[Feedback]:
        """
        Получить страницу активных отзывов с фильтрами.
        """

        conditions = [self.model.deleted_at.is_(None)]

        if filters is not None:
            if filters.rating is not None:
                conditions.append(self.model.rating == filters.rating)

            if filters.ticket_id is not None:
                conditions.append(self.model.ticket_id == filters.ticket_id)

            if filters.author_id is not None:
                conditions.append(self.model.author_id == filters.author_id)

        stmt = select(self.model).where(and_(*conditions))
        return await self._paginate(stmt, pagination)