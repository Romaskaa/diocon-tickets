from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.domain.services import get_display_user_role
from ...iam.domain.vo import UserRole
from ...iam.schemas import CurrentUser
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import NotFoundError
from ...shared.schemas import Page, PageParams
from ..domain.entities import Comment, Ticket
from ..domain.repos import CommentRepository, ReactionRepository, TicketRepository
from ..domain.services import can_access_ticket, can_comment_ticket
from ..domain.vo import CommentType
from ..mappers import map_comment_to_response, map_comment_with_reactions_to_response
from ..schemas import CommentCreate, CommentEdit, CommentResponse, CommentWithReactionsResponse


class CommentService:
    def __init__(
            self,
            session: AsyncSession,
            ticket_repo: TicketRepository,
            comment_repo: CommentRepository,
            reaction_repo: ReactionRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.ticket_repo = ticket_repo
        self.comment_repo = comment_repo
        self.reaction_repo = reaction_repo
        self.event_publisher = event_publisher

    @staticmethod
    def _prepare_comment(
            ticket: Ticket,
            current_user: CurrentUser,
            text: str,
            comment_type: CommentType,
            parent_comment: Comment | None = None,
    ) -> tuple[Comment, Comment | None]:
        """
        Подготовка комментария к записи в хранилище.
        Возвращает кортеж из нового комментария и его родителя.
        """

        # 1. Проверка прав на создание комментария
        permission = can_comment_ticket(
            ticket=ticket,
            user_id=current_user.user_id,
            user_role=current_user.role,
            user_counterparty_id=current_user.counterparty_id,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 2. Создание корневого комментария
        if parent_comment is None:
            comment = Comment.create(
                ticket_id=ticket.id,
                author_id=current_user.user_id,
                author_role=current_user.role,
                text=text,
                comment_type=comment_type,
            )
            ticket.write_history(
                actor_id=current_user.user_id,
                action="comment_added",
                description=(
                    f"{get_display_user_role(current_user.role)} добавил новый комментарий:"
                    f"'{comment.text[:100]}'"
                )
            )
            return comment, None

        # 3. Создание ответа на комментарий
        reply = parent_comment.create_reply(
            author_id=current_user.user_id,
            author_role=current_user.role,
            text=text,
            comment_type=comment_type,
        )
        ticket.write_history(
            actor_id=current_user.user_id,
            action="comment_added",
            description=(
                f"{get_display_user_role(current_user.role)} ответил на комментарий: "
                f"'{reply.text[:100]}'"
            )
        )

        return reply, parent_comment

    async def add_comment(
            self, ticket_id: UUID, data: CommentCreate, current_user: CurrentUser
    ) -> CommentResponse:
        """Добавление комментария к тикету"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Создание и сохранение комментария
        comment, _ = self._prepare_comment(
            ticket=ticket,
            current_user=current_user,
            text=data.text,
            comment_type=data.type,
        )
        await self.comment_repo.create(comment)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 3. Публикация доменных событий
        for event in comment.collect_events():
            await self.event_publisher.publish(event)

        return map_comment_to_response(comment)

    async def reply_to_comment(
            self,
            ticket_id: UUID,
            parent_comment_id: UUID,
            data: CommentCreate,
            current_user: CurrentUser,
    ) -> CommentResponse:
        """Добавление ответа на комментарий"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Получение родительского комментария
        parent_comment = await self.comment_repo.read(parent_comment_id)
        if parent_comment is None:
            raise NotFoundError(f"Comment with ID {parent_comment_id} not found")

        # 3. Проверка на, что комментарий принадлежит тикету
        if parent_comment.ticket_id != ticket_id:
            raise NotFoundError("Comment does not belong to this ticket")

        # 4. Создание и сохранение ответа
        reply, parent_comment = self._prepare_comment(
            ticket=ticket,
            current_user=current_user,
            text=data.text,
            comment_type=data.type,
            parent_comment=parent_comment,
        )
        await self.comment_repo.upsert(parent_comment)
        await self.comment_repo.create(reply)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in reply.collect_events():
            await self.event_publisher.publish(event)

        return map_comment_to_response(reply)

    async def edit_comment(
            self, ticket_id: UUID, comment_id: UUID, data: CommentEdit, edited_by: UUID
    ) -> CommentResponse:
        """Редактирование комментария"""

        # 1. Получение тикета и комментария
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        comment = await self.comment_repo.read(comment_id)
        if comment is None:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        # 2. Проверка на, что комментарий принадлежит тикету
        if comment.ticket_id != ticket_id:
            raise NotFoundError("Comment does not belong to this ticket")

        # 3. Редактирование комментария и обновление сущности
        old_text = comment.text
        comment.edit(new_text=data.text, edited_by=edited_by)
        if old_text != comment.text:  # Если текст изменён, то записывается в историю
            ticket.write_history(
                actor_id=edited_by,
                action="comment_edited",
                description=f"Комментарий отредактирован: '{data.text[:100]}'",
                old_value=comment.text[:100],
                new_value=data.text[:100],
            )
        await self.comment_repo.upsert(comment)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in comment.collect_events():
            await self.event_publisher.publish(event)

        return map_comment_to_response(comment)

    async def delete_comment(
            self, ticket_id: UUID, comment_id: UUID, deleted_by: UUID, deleted_by_role: UserRole
    ) -> None:
        """Удаление комментария"""

        # 1. Получение тикета и комментария
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        comment = await self.comment_repo.read(comment_id)
        if comment is None:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        # 2. Проверка на, что комментарий принадлежит тикету
        if comment.ticket_id != ticket_id:
            raise NotFoundError("Comment does not belong to this ticket")

        # 3. Если выбранный комментарий - ответ, то уменьшение счётчика ответов у родителя
        parent_comment = None
        if comment.is_reply:
            parent_comment = await self.comment_repo.read(comment.parent_comment_id)
            if parent_comment is not None and not parent_comment.is_deleted:
                parent_comment.decrement_reply_count()

        # 3. Удаление и запись в историю
        comment.delete(deleted_by=deleted_by, deleted_by_role=deleted_by_role)
        ticket.write_history(
            actor_id=deleted_by,
            action="comment_deleted",
            description=(
                f"{get_display_user_role(deleted_by_role)} удалил комментарий: "
                f"'{comment.text[:100]}'"
            ),
            old_value=comment.text[:100],
            new_value=None,
        )

        await self.comment_repo.upsert(comment)

        if parent_comment is not None:
            await self.comment_repo.upsert(parent_comment)

        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

    async def get_comments(
            self,
            ticket_id: UUID,
            pagination: PageParams,
            current_user: CurrentUser,
            include_internal: bool = False,
    ) -> Page[CommentWithReactionsResponse]:
        """Получение комментариев к тикету с учётом прав"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Имеется ли у пользователя доступ к тикету
        permission = can_access_ticket(
            ticket,
            user_id=current_user.user_id,
            user_role=current_user.role,
            user_counterparty_id=current_user.counterparty_id,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Проверка прав на просмотр внутренних комментариев
        if include_internal and not current_user.role.is_support():
            raise PermissionDeniedError("Only support team can view internal comments")

        # 4. Получение комментариев + загрузка реакций
        page = await self.comment_repo.get_by_ticket(
            ticket_id=ticket_id,
            pagination=pagination,
            user_id=current_user.user_id,
            include_notes=True,
            include_internal=include_internal,
        )

        comment_ids = [comment.id for comment in page.items]
        stats = await self.reaction_repo.get_reaction_stats(comment_ids, current_user.user_id)

        # 5. Маппинг реакций к комментарию
        def mapper(comment: Comment) -> CommentWithReactionsResponse:
            return map_comment_with_reactions_to_response(
                comment=comment,
                reaction_counts=stats.counts.get(comment.id, {}),
                user_reactions=list(stats.user_reactions.get(comment.id, set())),
            )

        return page.to_response(mapper)

    async def get_comment_replies(
            self,
            comment_id: UUID,
            pagination: PageParams,
            current_user: CurrentUser,
            include_internal: bool = False,
    ) -> Page[CommentWithReactionsResponse]:
        """Получение дерево ответов на комментарий"""

        # 1. Проверка существования и доступности родителя
        parent_comment = await self.comment_repo.read(comment_id)
        if parent_comment is None or parent_comment.is_deleted:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        ticket = await self.ticket_repo.read(parent_comment.ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {comment_id} not found")

        permission = can_access_ticket(
            ticket=ticket,
            user_id=current_user.user_id,
            user_role=current_user.role,
            user_counterparty_id=current_user.counterparty_id,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        if include_internal and not current_user.role.is_support():
            raise PermissionDeniedError("Only support team can view internal comments")

        # 2. Получение ответов на комментарий и загрузка реакций
        page = await self.comment_repo.get_replies(
            parent_comment_id=parent_comment.id,
            pagination=pagination,
            user_id=current_user.user_id,
            include_internal=include_internal,
        )

        comment_ids = [comment.id for comment in page.items]
        stats = await self.reaction_repo.get_reaction_stats(comment_ids, current_user.user_id)

        # 3. Маппинг реакций к комментарию
        def mapper(comment: Comment) -> CommentWithReactionsResponse:
            return map_comment_with_reactions_to_response(
                comment=comment,
                reaction_counts=stats.counts.get(comment.id, {}),
                user_reactions=list(stats.user_reactions.get(comment.id, set())),
            )

        return page.to_response(mapper)
