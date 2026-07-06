from typing import override

from collections import defaultdict
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import selectinload

from src.shared.infra.repos import SqlAlchemyRepository
from src.shared.schemas import Page, Pagination

from ..domain.dtos import ActorsFilters
from ..domain.entities import Comment, Reaction, Ticket
from ..domain.repos import ReactionStats, TicketFilters
from ..domain.vo import CommentType, ReactionType
from .mappers import CommentMapper, ReactionMapper, TicketMapper
from .models import CommentOrm, ReactionOrm, TicketOrm


class SqlTicketRepository(SqlAlchemyRepository[Ticket, TicketOrm]):
    model = TicketOrm
    model_mapper = TicketMapper

    @override
    async def read(self, ticket_id: UUID) -> Ticket | None:
        stmt = (
            select(self.model)
            .where(self.model.id == ticket_id)
            .options(selectinload(self.model.attachments))
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return None if model is None else self.model_mapper.to_entity(model)

    def _apply_actors_filters(
            self, stmt: Select[tuple[TicketOrm]], filters: ActorsFilters,
    ) -> Select[tuple[TicketOrm]]:
        if filters.assignee_id:
            stmt = stmt.where(self.model.assignee_id == filters.assignee_id)

        if filters.reporter_id:
            stmt = stmt.where(self.model.reporter_id == filters.reporter_id)

        if filters.creator_id:
            stmt = stmt.where(self.model.created_by == filters.creator_id)

        return stmt

    def _apply_ticket_filters(
            self, stmt: Select[tuple[TicketOrm]], filters: TicketFilters,
    ) -> Select[tuple[TicketOrm]]:
        if filters.statuses:
            stmt = stmt.where(self.model.status.in_(filters.statuses))

        if filters.priorities:
            stmt = stmt.where(self.model.priority.in_(filters.priorities))

        if filters.type:
            stmt = stmt.where(self.model.ticket_type == filters.type)

        if filters.tags:
            tag_conditions = [self.model.tags.contains([{"name": tag}]) for tag in filters.tags]
            stmt = stmt.where(or_(*tag_conditions))

        if filters.search_query:
            stmt = stmt.where(
                self.model.search_vector.op("@@")(
                    func.plainto_tsquery("russian", filters.search_query)
                )
            )

        if filters.actors:
            stmt = self._apply_actors_filters(stmt, filters.actors)

        if filters.time_range:
            stmt = self._apply_time_range_filters(stmt, filters.time_range)

        return stmt

    @override
    async def paginate(
            self, pagination: Pagination, filters: TicketFilters | None = None,
    ) -> Page[Ticket]:
        stmt = select(self.model)

        if filters is not None:
            stmt = self._apply_ticket_filters(stmt, filters)

        return await self._paginate(stmt, pagination, model_mapper=self.model_mapper.to_light)

    async def get_total(
            self, project_id: UUID | None = None, counterparty_id: UUID | None = None
    ) -> int:
        conditions = []

        if project_id is not None:
            conditions.append(self.model.project_id == project_id)
            if counterparty_id is not None:
                conditions.append(self.model.counterparty_id == counterparty_id)

        elif counterparty_id is not None and project_id is None:
            conditions.extend((
                self.model.counterparty_id == counterparty_id,
                self.model.project_id.is_(None)
            ))

        else:
            conditions.extend((
                self.model.project_id.is_(None), self.model.counterparty_id.is_(None),
            ))

        stmt = select(func.count()).select_from(self.model).where(and_(*conditions))
        return await self.session.scalar(stmt) or 0

    async def get_by_reporter(self, reporter_id: UUID, pagination: Pagination) -> Page[Ticket]:
        stmt = select(self.model).where(self.model.reporter_id == reporter_id)

        return await self._paginate(stmt, pagination)


class SqlCommentRepository(SqlAlchemyRepository[Comment, CommentOrm]):
    model = CommentOrm
    model_mapper = CommentMapper

    async def get_by_ticket(
            self,
            ticket_id: UUID,
            pagination: Pagination,
            *,
            user_id: UUID | None = None,
            include_notes: bool = False,
            include_internal: bool = False,
    ) -> Page[Comment]:
        # 1. Валидация входных параметров
        if user_id is None and include_notes:
            raise ValueError("User ID required for received NOTE comments")

        # 2. Список условий (фильтров)
        base_conditions = [
            self.model.ticket_id == ticket_id,
            self.model.parent_comment_id.is_(None),
            self.model.deleted_at.is_(None),
        ]
        type_conditions = [self.model.comment_type == CommentType.PUBLIC]

        # 3. Применение фильтров к запросу
        if include_notes:
            type_conditions.append(
                (self.model.comment_type == CommentType.NOTE) &
                (self.model.author_id == user_id)
            )
        if include_internal:
            type_conditions.append(self.model.comment_type == CommentType.INTERNAL)

        # 4. Формирование запроса
        stmt = select(self.model).where(
            and_(*base_conditions), or_(*type_conditions)
        )

        return await self._paginate(stmt, pagination)

    async def get_replies(
            self,
            parent_comment_id: UUID,
            pagination: Pagination,
            *,
            user_id: UUID | None = None,
            include_notes: bool = False,
            include_internal: bool = False,
    ) -> Page[Comment]:
        # 1. Применение фильтров по типу комментария
        type_conditions = [self.model.comment_type == CommentType.PUBLIC]
        if include_internal:
            type_conditions.append(self.model.comment_type == CommentType.INTERNAL)
        if include_notes:
            type_conditions.append(
                (self.model.comment_type == CommentType.NOTE) &
                (self.model.author_id == user_id)
            )

        stmt = select(self.model).where(
            self.model.parent_comment_id == parent_comment_id,
            self.model.deleted_at.is_(None),
            or_(*type_conditions),
        )

        return await self._paginate(stmt, pagination)


class SqlReactionRepository(SqlAlchemyRepository[Reaction, ReactionOrm]):
    model = ReactionOrm
    model_mapper = ReactionMapper

    async def find(
            self, comment_id: UUID, author_id: UUID, reaction_type: ReactionType
    ) -> Reaction | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.comment_id == comment_id) &
                (self.model.author_id == author_id) &
                (self.model.reaction_type == reaction_type)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_reaction_stats(self, comment_ids: list[UUID], user_id: UUID) -> ReactionStats:
        # 1. Запрос для получения реакции для списка комментариев
        stmt = (
            select(
                self.model.comment_id,
                self.model.reaction_type,
                func.count(self.model.id).label("cnt"),
                func.count(self.model.id)
                .filter(self.model.author_id == user_id)
                .label("user_has_type")
            )
            .where(
                (self.model.comment_id.in_(comment_ids)) &
                (self.model.deleted_at.is_(None))
            )
            .group_by(self.model.comment_id, self.model.reaction_type)
        )

        # 2. Формирование статистики для реакций
        result = await self.session.execute(stmt)

        counts: dict[UUID, dict[ReactionType, int]] = defaultdict(dict)
        user_reactions: dict[UUID, set[ReactionType]] = defaultdict(set)

        for row in result:
            counts[row.comment_id][row.reaction_type] = row.cnt
            if row.user_has_type > 0:
                user_reactions[row.comment_id].add(row.reaction_type)

        return ReactionStats(counts=counts, user_reactions=user_reactions)
