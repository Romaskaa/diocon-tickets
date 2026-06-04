from typing import Literal, override

from dataclasses import dataclass
from uuid import UUID

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from ..schemas import TicketFilter
from .entities import Comment, Membership, Project, Reaction, Ticket
from .vo import ProjectKey, ReactionType


class TicketRepository(Repository[Ticket]):
    @override
    async def read(self, ticket_id: UUID, comments_limit: int = 10) -> Ticket | None:
        """
        Получение тикета с лимитом на количество комментариев (для производительности)
        """

    @override
    async def paginate(
            self, params: PageParams, filters: TicketFilter | None = None
    ) -> Page[Ticket]:
        """Фильтрация тикетов"""

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

    async def get_by_reporter(self, reporter_id: UUID, params: PageParams) -> Page[Ticket]:
        """Получение тикетов по его инициатору"""


class CommentRepository(Repository[Comment]):

    async def get_by_ticket(
            self,
            ticket_id: UUID,
            pagination: PageParams,
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
        pagination: PageParams,
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
    ) -> Reaction | None:
        """Получение реакции пользователя на комментарий"""

    async def get_reaction_stats(self, comment_ids: list[UUID], user_id: UUID) -> ReactionStats:
        """
        Получение информации о реакциях для каждого комментария из списка
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


class ProjectRepository(Repository[Project]):

    async def get_by_key(self, key: ProjectKey) -> Project | None:
        """Получение проекта по его уникальному ключу"""

    async def get_existing_keys(self, keys: list[str]) -> set[str]:
        """
        Возвращает множество ключей, которые уже существуют.
        Оптимизировано для пакетной проверки.
        """

    async def get_membership(self, project_id: UUID, user_id: UUID) -> Membership | None:
        """
        Получение участника проекта
        """

    async def get_by_user_membership(
            self,
            user_id: UUID,
            pagination: PageParams,
            role: Literal["owner", "member", "all"] = "all",
    ) -> Page[Project]:
        """
        Получение проектов пользователя в зависимости от параметра role:

         - 'owner' - проекты, где пользователь является владельцем.
         - 'member' - пользователь любой другой участник, кроме владельца.
         - 'all' - любой участник (на важно какая роль).
        """
