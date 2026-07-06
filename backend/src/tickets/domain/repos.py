from typing import override

from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.repos import Repository
from src.shared.schemas import Page, Pagination

from .dtos import TicketFilters
from .entities import Comment, Reaction, Ticket
from .vo import ReactionType


class TicketRepository(Repository[Ticket]):
    @override
    async def paginate(
            self, pagination: Pagination, filters: TicketFilters | None = None,
    ) -> Page[Ticket]: ...

    async def get_total(
            self, project_id: UUID | None = None, counterparty_id: UUID | None = None
    ) -> int:
        """
        Получение общего числа тикетов.
        Поддерживает 3 сценария получения количества:
         - Внутренних тикетов (проект и контрагент не указаны)
         - Тикеты в рамках проекта (указан проект + 'опционально' контрагент)
         - Принадлежащие контрагенту (указан контрагент, проект не указан)
        """

    async def get_by_reporter(self, reporter_id: UUID, params: Pagination) -> Page[Ticket]: ...


class CommentRepository(Repository[Comment]):

    async def get_by_ticket(
            self,
            ticket_id: UUID,
            pagination: Pagination,
            *,
            user_id: UUID | None = None,
            include_notes: bool = False,
            include_internal: bool = False,
    ) -> Page[Comment]:
        """
        Получение списка комментариев с учётом фильтров и прав пользователя
        """

    async def get_replies(
        self,
        parent_comment_id: UUID,
        pagination: Pagination,
        *,
        user_id: UUID | None = None,
        include_notes: bool = False,
        include_internal: bool = False,
    ) -> Page[Comment]:
        """
        Получение вложенных ответов на комментарий (дерево комментариев)
        """


@dataclass(frozen=True, slots=True)
class ReactionStats:
    """
    Агрегированные данные о реакциях на комментарии
    """

    counts: dict[UUID, dict[ReactionType, int]]
    user_reactions: dict[UUID, set[ReactionType]]


class ReactionRepository(Repository[Reaction]):

    async def find(
            self, comment_id: UUID, author_id: UUID, reaction_type: ReactionType
    ) -> Reaction | None: ...

    async def get_reaction_stats(self, comment_ids: list[UUID], user_id: UUID) -> ReactionStats:
        """
        Получить агрегированные данные о реакциях для каждого комментария из списка.
        """

    async def get_counts(self, comment_ids: list[UUID]) -> dict[UUID, dict[ReactionType, int]]:
        """
        Получение счётчиков реакций для комментариев.
        Принимает список ID комментариев для избежания N+1.
        Маппинг: реакция -> количество ('like' -> 5).
        """

    async def get_user_reactions(
            self, comments_ids: list[UUID], author_id: UUID
    ) -> dict[UUID, set[ReactionType]]:
        """
        Получение реакций пользователя на комментарии.
        Принимает список ID комментариев для избежания N+1.
        На выходе маппинг Comment ID -> ['like', 'in_progress', ..., 'resolved'].
        """
