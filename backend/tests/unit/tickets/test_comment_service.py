from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.shared.domain.exceptions import NotFoundError
from src.shared.schemas import PageParams
from src.tickets.domain.entities import Comment, Reaction, Ticket
from src.tickets.domain.vo import CommentType, ReactionType, TicketNumber
from src.tickets.schemas import CommentCreate
from src.tickets.services import CommentService


@pytest.fixture
def comment_service(
        mock_session,
        mock_ticket_repo,
        mock_comment_repo,
        mock_reaction_repo,
        event_publisher,
):
    return CommentService(
        session=mock_session,
        ticket_repo=mock_ticket_repo,
        comment_repo=mock_comment_repo,
        reaction_repo=mock_reaction_repo,
        event_publisher=event_publisher,
    )


@pytest.fixture
def customer_id():
    return uuid4()


@pytest.fixture
def counterparty_id():
    return uuid4()


@pytest.fixture
def current_support_user(counterparty_id):
    return CurrentUser(
        user_id=uuid4(),
        email="support@example.com",
        role=UserRole.SUPPORT_AGENT,
    )


@pytest.fixture
def current_customer_user(counterparty_id, customer_id):
    return CurrentUser(
        user_id=customer_id,
        email="customer@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=counterparty_id,
    )


@pytest.fixture
async def created_ticket(customer_id, counterparty_id, mock_ticket_repo):
    ticket = Ticket.create(
        ticket_number=TicketNumber("TEST-26-00000001"),
        reporter_id=customer_id,
        created_by=uuid4(),
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        counterparty_id=counterparty_id,
    )
    await mock_ticket_repo.create(ticket)
    return ticket


@pytest.fixture
async def created_comment(created_ticket, mock_comment_repo, customer_id):
    comment = Comment.create(
        ticket_id=created_ticket.id,
        author_id=customer_id,
        author_role=UserRole.CUSTOMER,
        text="Комментарий клиента"
    )
    await mock_comment_repo.create(comment)
    return comment


class TestAddComment:
    """
    Тестирование добавления комментария
    """

    @pytest.mark.asyncio
    async def test_creates_success(
            self,
            mock_session,
            mock_comment_repo,
            comment_service,
            current_support_user,
            created_ticket,
    ):
        """
        Успешное создание комментария
        """

        data = CommentCreate(text="Тестовый комментарий  ", type=CommentType.PUBLIC)
        response = await comment_service.add_comment(
            ticket_id=created_ticket.id, data=data, current_user=current_support_user
        )

        mock_session.commit.assert_awaited_once()

        assert response.text == data.text.strip()
        assert response.ticket_id == created_ticket.id
        assert response.type == CommentType.PUBLIC

        added_comment = await mock_comment_repo.read(response.id)

        assert added_comment is not None
        assert added_comment.text == data.text.strip()

    @pytest.mark.asyncio
    async def test_fails_on_permission_denied_no_commit(
            self, mock_session, comment_service, created_ticket
    ):
        """
        Комментарий не должен сохраняться если недостаточно прав
        """

        data = CommentCreate(text="Тестовый комментарий", type=CommentType.PUBLIC)
        current_user = CurrentUser(
            user_id=uuid4(),
            email="customer@example.com",
            role=UserRole.CUSTOMER,
            counterparty_id=uuid4(),
        )

        with pytest.raises(PermissionDeniedError):
            await comment_service.add_comment(
                ticket_id=created_ticket.id, data=data, current_user=current_user
            )

        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_fails_on_not_found_error(self, comment_service, current_support_user):
        """
        Нельзя комментировать несуществующий тикет
        """

        data = CommentCreate(text="тестовый комментарий", type=CommentType.PUBLIC)
        with pytest.raises(NotFoundError):
            await comment_service.add_comment(
                ticket_id=uuid4(), data=data, current_user=current_support_user
            )


class TestReplyToComment:
    """
    Тесты для ответа на комментарий
    """

    @pytest.mark.asyncio
    async def test_success_creates_reply_and_upsert_parent(
            self,
            comment_service,
            current_support_user,
            mock_session,
            mock_comment_repo,
            created_ticket,
            created_comment,
    ):
        """
        Успешное создание ответа и обновление корневого комментария
        """

        data = CommentCreate(text="Тестовый комментарий", type=CommentType.PUBLIC)
        response = await comment_service.reply_to_comment(
            ticket_id=created_ticket.id,
            parent_comment_id=created_comment.id,
            data=data,
            current_user=current_support_user,
        )

        mock_session.commit.assert_awaited_once()

        parent_comment = await mock_comment_repo.read(response.parent_comment_id)

        assert parent_comment is not None
        assert parent_comment.reply_count == 1

        assert response.text == data.text.strip()

    @pytest.mark.asyncio
    async def test_fails_when_comment_does_not_belong_ticket(
            self,
            comment_service,
            mock_session,
            mock_ticket_repo,
            created_comment,
            current_customer_user,
    ):
        """
        Нельзя создать ответ если родительский комментарий не принадлежит тикету
        """

        # Добавление левого тикета
        ticket = Ticket.create(
            ticket_number=TicketNumber("TEST1-26-00000002"),
            reporter_id=uuid4(),
            created_by=uuid4(),
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Какой-то левый тикет",
            description="Описание",
        )
        await mock_ticket_repo.create(ticket)

        data = CommentCreate(text="Тестовый комментарий", type=CommentType.PUBLIC)

        with pytest.raises(NotFoundError, match="Comment does not belong to this ticket"):
            await comment_service.reply_to_comment(
                ticket_id=ticket.id,
                parent_comment_id=created_comment.id,
                data=data,
                current_user=current_customer_user,
            )

        mock_session.commit.assert_not_called()


class TestDeleteComment:
    """
    Тесты для удаления комментария (Soft-delete)
    """

    @pytest.mark.asyncio
    async def test_success_deletes_comment(
            self,
            comment_service,
            current_customer_user,
            created_comment,
            mock_session,
            mock_comment_repo,
    ):
        """
        Успешное удаление комментария
        """

        await comment_service.delete_comment(
            ticket_id=created_comment.ticket_id,
            comment_id=created_comment.id,
            deleted_by=current_customer_user.user_id,
            deleted_by_role=current_customer_user.role,
        )

        mock_session.commit.assert_awaited_once()

        existing = await mock_comment_repo.read(created_comment.id)

        assert existing.is_deleted is True

    @pytest.mark.asyncio
    async def test_success_deleted_reply_and_decrement_parent_counter(
            self,
            comment_service,
            current_support_user,
            created_ticket,
            created_comment,
            mock_comment_repo,
    ):
        """
        Успешное удаление ответа и уменьшение счётчика ответов у родителя
        """

        data = CommentCreate(text="Тестовый комментарий", type=CommentType.PUBLIC)
        response = await comment_service.reply_to_comment(
            ticket_id=created_ticket.id,
            parent_comment_id=created_comment.id,
            data=data,
            current_user=current_support_user,
        )

        await comment_service.delete_comment(
            ticket_id=created_ticket.id,
            comment_id=response.id,
            deleted_by=current_support_user.user_id,
            deleted_by_role=current_support_user.role,
        )

        existing = await mock_comment_repo.read(response.id)
        assert existing.is_deleted is True

        parent_comment = await mock_comment_repo.read(created_comment.id)
        assert parent_comment is not None
        assert parent_comment.reply_count == 0

    @pytest.mark.asyncio
    async def test_fails_when_comment_does_not_belong_ticket(
            self,
            comment_service,
            current_customer_user,
            created_comment,
            mock_ticket_repo,
    ):
        """
        Нельзя удалить комментарий не принадлежащий тикету
        """

        # Добавление левого тикета
        ticket = Ticket.create(
            ticket_number=TicketNumber("TEST1-26-00000002"),
            reporter_id=uuid4(),
            created_by=uuid4(),
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Какой-то левый тикет",
            description="Описание",
        )
        await mock_ticket_repo.create(ticket)

        with pytest.raises(NotFoundError, match="Comment does not belong to this ticket"):
            await comment_service.delete_comment(
                ticket_id=ticket.id,
                comment_id=created_comment.id,
                deleted_by=current_customer_user.user_id,
                deleted_by_role=current_customer_user.role,
            )

    @pytest.mark.asyncio
    async def test_skip_decrement_counter_if_parent_is_deleted(
            self,
            comment_service,
            current_customer_user,
            current_support_user,
            created_ticket,
            created_comment,
            mock_comment_repo,
    ):
        """
        Пропуск уменьшения счётчика, если родитель был удалён
        """

        # 1. Создание ответа
        data = CommentCreate(text="Ответ на комментарий", type=CommentType.PUBLIC)
        response = await comment_service.reply_to_comment(
            ticket_id=created_ticket.id,
            parent_comment_id=created_comment.id,
            data=data,
            current_user=current_support_user,
        )

        # 2. Удаление корневого комментария
        await comment_service.delete_comment(
            ticket_id=created_ticket.id,
            comment_id=created_comment.id,
            deleted_by=current_customer_user.user_id,
            deleted_by_role=current_customer_user.role,
        )

        # 3. Удаление ответа
        await comment_service.delete_comment(
            ticket_id=created_ticket.id,
            comment_id=response.id,
            deleted_by=current_support_user.user_id,
            deleted_by_role=current_support_user.role,
        )

        parent_comment = await mock_comment_repo.read(created_comment.id)
        assert parent_comment is not None
        assert parent_comment.is_deleted is True
        assert parent_comment.reply_count == 1


class TestEditComment:
    """
    Тесты для редактирования комментария
    """


class TestGetComments:
    """
    Тесты для получения списка комментариев
    """

    @pytest.fixture
    async def sample_comments(
            self, created_ticket, mock_comment_repo, mock_reaction_repo, current_support_user
    ):
        first_comment = Comment.create(
            ticket_id=created_ticket.id,
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_AGENT,
            text="Первый комментарий"
        )
        comments = [
            first_comment,
            first_comment.create_reply(
                author_id=uuid4(),
                author_role=UserRole.CUSTOMER,
                text="Ответ на первый комментарий"
            ),
            Comment.create(
                ticket_id=created_ticket.id,
                author_id=uuid4(),
                author_role=UserRole.SUPPORT_MANAGER,
                text="Второй комментарий",
            ),
            Comment.create(
                ticket_id=created_ticket.id,
                author_id=uuid4(),
                author_role=UserRole.CUSTOMER_ADMIN,
                text="Третий комментарий"
            ),
            Comment.create(
                ticket_id=created_ticket.id,
                author_id=uuid4(),
                author_role=UserRole.SUPPORT_MANAGER,
                text="Внутренний комментарий",
                comment_type=CommentType.INTERNAL,
            )
        ]
        for comment in comments:
            await mock_comment_repo.create(comment)

        reaction = Reaction.create(
            comment_id=first_comment.id,
            author_id=current_support_user.user_id,
            author_role=current_support_user.role,
            reaction_type=ReactionType.LIKE,
        )
        await mock_reaction_repo.create(reaction)

        return comments

    @pytest.mark.asyncio
    async def test_success_returns_paginated_with_stats(
            self,
            comment_service,
            current_support_user,
            created_ticket,
            sample_comments,
    ):
        """
        Успешное получение списка комментариев с реакциями
        """

        response = await comment_service.get_comments(
            ticket_id=created_ticket.id,
            pagination=PageParams(page=1, size=5),
            current_user=current_support_user,
            include_internal=True,
        )

        assert len(response.items) == len(sample_comments) - 1  # без учёта одного ответа
        assert all(comment.parent_comment_id is None for comment in response.items)

        first_comment = response.items[0]
        assert first_comment.reaction_counts.get(ReactionType.LIKE, 0) == 1
        assert ReactionType.LIKE in first_comment.user_reactions

    @pytest.mark.asyncio
    async def test_fails_if_internal_requested_by_non_support(
            self,
            comment_service,
            current_customer_user,
            sample_comments,  # noqa: ARG002
            created_ticket,
    ):
        """
        Клиент не может видеть внутренний комментарий
        """

        with pytest.raises(PermissionDeniedError):
            await comment_service.get_comments(
                ticket_id=created_ticket.id,
                pagination=PageParams(page=1, size=5),
                current_user=current_customer_user,
                include_internal=True,
            )


class TestGetReplies:
    """
    Тесты для получения списка ответов на комментарий
    """
