from dataclasses import dataclass
from uuid import UUID
from typing import Self

from src.shared.domain.entities import AggregateRoot
from src.shared.utils.time import current_datetime

from .events import FeedbackCreated
from .vo import FeedbackRating


@dataclass(kw_only=True)
class Feedback(AggregateRoot):
    """
    Отзыв клиента о качестве обслуживания по закрутому тикету.
    """
    
    ticket_id: UUID
    author_id: UUID
    rating: FeedbackRating
    comment: str | None = None

    def __post_init__(self) -> None:
        """
        Нормализует комментарий отзыва после создания объекта.
        """

        self.comment = self._normalize_comment(self.comment)

    @classmethod
    def create(
        cls, 
        *, 
        ticket_id: UUID, 
        author_id: UUID, 
        rating: int, 
        comment: str | None = None
    ) -> Self:
        """
        Создаёт новый отзыв клиента.
        """

        feedback = cls(
            ticket_id=ticket_id,
            author_id=author_id,
            rating=FeedbackRating(rating),
            comment=comment,
        )

        feedback.register_event(
            FeedbackCreated(
                feedback_id=feedback.id,
                ticket_id=ticket_id,
                author_id=author_id,
                rating=feedback.rating.value,
                comment=feedback.comment,
            )
        )

        return feedback
    
    def edit(
        self,
        *,
        rating: int | None = None,
        comment: str | None = None,
    ) -> None:
        """
        Редактирует оценку и комментарий отзыва.
        Если данные изменились, то обновляет updated_at.
        """

        is_edited = False

        if rating is not None:
            new_rating = FeedbackRating(rating)

            if new_rating != self.rating:
                self.rating = new_rating
                is_edited = True

        if comment is not None:
            normalized_comment = self._normalize_comment(comment)

            if normalized_comment != self.comment:
                self.comment = normalized_comment
                is_edited = True

        if is_edited:
            self.updated_at = current_datetime()

    def archive(self) -> None:
        """
        Архивирует отзыв через мягкое удаление.
        """

        if self.is_deleted:
            return
        
        self.deleted_at = current_datetime()
        self.updated_at = current_datetime()
        
    @staticmethod
    def _normalize_comment(comment: str | None) -> str | None:
        """
        Убирает лишние пробелы из комментария.
        """

        if comment is None:
            return None
        
        normalized = comment.strip()
        return normalized or None