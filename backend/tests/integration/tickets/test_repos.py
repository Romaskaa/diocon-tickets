from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.shared.schemas import PageParams
from src.tickets.domain.entities import Comment, Project, Reaction, Ticket
from src.tickets.domain.vo import (
    CommentType,
    ProjectRole,
    ReactionType,
    Tag,
    TicketNumber,
    TicketPriority,
    TicketStatus,
)
from src.tickets.infra.repos import (
    SqlCommentRepository,
    SqlProjectRepository,
    SqlReactionRepository,
    SqlTicketRepository,
)
from src.tickets.schemas import TicketFilter


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def ticket_repo(session):
    return SqlTicketRepository(session)


@pytest.fixture
def comment_repo(session):
    return SqlCommentRepository(session)


@pytest.fixture
def reaction_repo(session):
    return SqlReactionRepository(session)


@pytest.fixture
async def saved_project(session, project_repo):
    owner_id = uuid4()
    project = Project.create(
        name=f"Проект поддержки {uuid4()}",
        key=f"P{uuid4().hex[:5].upper()}",
        owner_id=owner_id,
        created_by=owner_id,
        description="Проект поддержки",
    )
    await project_repo.create(project)
    await session.commit()
    return project


@pytest.fixture
async def saved_ticket(session, ticket_repo):
    ticket = Ticket.create(
        ticket_number=TicketNumber(f"INT-26-{uuid4().int % 10**8:08d}"),
        reporter_id=uuid4(),
        created_by=uuid4(),
        created_by_role=UserRole.ADMIN,
        title=f"Интеграционный тикет {uuid4()}",
        description="Тикет для интеграционных тестов репозитория",
        priority=TicketPriority.HIGH,
        tags=[Tag(name="integration", color="#3498db")],
    )
    await ticket_repo.create(ticket)
    await session.commit()
    return ticket


@pytest.fixture
async def saved_comment(session, comment_repo, saved_ticket):
    comment = Comment.create(
        ticket_id=saved_ticket.id,
        author_id=uuid4(),
        author_role=UserRole.SUPPORT_AGENT,
        text="Публичный комментарий",
        comment_type=CommentType.PUBLIC,
    )
    await comment_repo.create(comment)
    await session.commit()
    return comment


@pytest.mark.integration
class TestSqlProjectRepository:
    @pytest.mark.asyncio
    async def test_get_by_key_returns_project_with_owner_membership(
            self, project_repo, saved_project
    ):
        """
        Репозиторий возвращает проект по ключу вместе с owner membership.
        Это основной поиск для сервисов проектов и проверки прав.
        """

        found_project = await project_repo.get_by_key(saved_project.key)

        assert found_project is not None
        assert found_project.id == saved_project.id
        assert found_project.key == saved_project.key
        assert found_project.owner_id == saved_project.owner_id
        assert found_project.memberships[0].project_role == ProjectRole.OWNER


@pytest.mark.integration
class TestSqlTicketRepository:
    @pytest.mark.asyncio
    async def test_read_returns_ticket_with_history(self, ticket_repo, saved_ticket):
        """
        Репозиторий загружает агрегат тикета вместе с историей создания.
        Потеря history ломает аудит и пользовательскую ленту изменений.
        """

        found_ticket = await ticket_repo.read(saved_ticket.id)

        assert found_ticket is not None
        assert found_ticket.id == saved_ticket.id
        assert found_ticket.number == saved_ticket.number
        assert found_ticket.title == saved_ticket.title
        assert len(found_ticket.history) == 1
        assert found_ticket.history[0].action == "ticket_created"

    @pytest.mark.asyncio
    async def test_paginate_applies_status_priority_and_tag_filters(
            self, ticket_repo, saved_ticket
    ):
        """
        Репозиторий применяет основные фильтры списка тикетов из рабочей очереди.
        """

        page = await ticket_repo.paginate(
            params=PageParams(page=1, size=10),
            filters=TicketFilter(
                status=TicketStatus.NEW,
                priority=TicketPriority.HIGH,
                tags=["integration"],
            ),
        )

        found_ids = {ticket.id for ticket in page.items}
        assert saved_ticket.id in found_ids
        assert all(ticket.status == TicketStatus.NEW for ticket in page.items)
        assert all(ticket.priority == TicketPriority.HIGH for ticket in page.items)

    @pytest.mark.asyncio
    async def test_get_by_reporter_returns_only_reporter_tickets(
            self, session, ticket_repo, saved_ticket
    ):
        """
        Репозиторий возвращает только тикеты конкретного инициатора.
        Это основной сценарий для списка "мои тикеты".
        """
        other_ticket = Ticket.create(
            ticket_number=TicketNumber(f"INT-26-{uuid4().int % 10**8:08d}"),
            reporter_id=uuid4(),
            created_by=uuid4(),
            created_by_role=UserRole.ADMIN,
            title=f"Чужой тикет {uuid4()}",
            description="Тикет другого инициатора",
            priority=TicketPriority.HIGH,
        )
        await ticket_repo.create(other_ticket)
        await session.commit()

        page = await ticket_repo.get_by_reporter(
            reporter_id=saved_ticket.reporter_id,
            params=PageParams(page=1, size=10),
        )

        found_ids = {ticket.id for ticket in page.items}
        assert saved_ticket.id in found_ids
        assert other_ticket.id not in found_ids
        assert all(ticket.reporter_id == saved_ticket.reporter_id for ticket in page.items)


@pytest.mark.integration
class TestSqlCommentRepository:
    @pytest.mark.asyncio
    async def test_get_by_ticket_hides_internal_comments_by_default(
            self, session, comment_repo, saved_ticket, saved_comment
    ):
        """
        Репозиторий скрывает internal-комментарии из публичного списка,
        пока они не запрошены явно.
        """
        internal_comment = Comment.create(
            ticket_id=saved_ticket.id,
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_MANAGER,
            text="Внутренняя заметка",
            comment_type=CommentType.INTERNAL,
        )
        await comment_repo.create(internal_comment)
        await session.commit()

        public_page = await comment_repo.get_by_ticket(
            ticket_id=saved_ticket.id,
            pagination=PageParams(page=1, size=10),
        )
        internal_page = await comment_repo.get_by_ticket(
            ticket_id=saved_ticket.id,
            pagination=PageParams(page=1, size=10),
            include_internal=True,
        )

        public_ids = {item.id for item in public_page.items}
        internal_ids = {item.id for item in internal_page.items}

        assert saved_comment.id in public_ids
        assert internal_comment.id not in public_ids
        assert internal_comment.id in internal_ids

    @pytest.mark.asyncio
    async def test_get_replies_hides_internal_replies_by_default(
            self, session, comment_repo, saved_comment
    ):
        """
        Репозиторий скрывает internal-ответы из публичного дерева replies,
        пока они не запрошены явно.
        """
        public_reply = saved_comment.create_reply(
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_AGENT,
            text="Публичный ответ",
            comment_type=CommentType.PUBLIC,
        )
        internal_reply = saved_comment.create_reply(
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_MANAGER,
            text="Внутренний ответ",
            comment_type=CommentType.INTERNAL,
        )
        await comment_repo.create(public_reply)
        await comment_repo.create(internal_reply)
        await session.commit()

        public_page = await comment_repo.get_replies(
            parent_comment_id=saved_comment.id,
            pagination=PageParams(page=1, size=10),
        )
        internal_page = await comment_repo.get_replies(
            parent_comment_id=saved_comment.id,
            pagination=PageParams(page=1, size=10),
            include_internal=True,
        )

        public_ids = {item.id for item in public_page.items}
        internal_ids = {item.id for item in internal_page.items}

        assert public_reply.id in public_ids
        assert internal_reply.id not in public_ids
        assert internal_reply.id in internal_ids


@pytest.mark.integration
class TestSqlReactionRepository:
    @pytest.mark.asyncio
    async def test_get_reaction_stats_returns_counts_and_user_reactions(
            self, session, reaction_repo, saved_comment
    ):
        """
        Репозиторий возвращает счетчики реакций и реакции текущего пользователя
        одним результатом для отображения комментариев.
        """
        user_id = uuid4()
        reactions = [
            Reaction.create(
                comment_id=saved_comment.id,
                author_id=user_id,
                author_role=UserRole.SUPPORT_AGENT,
                reaction_type=ReactionType.LIKE,
            ),
            Reaction.create(
                comment_id=saved_comment.id,
                author_id=uuid4(),
                author_role=UserRole.SUPPORT_MANAGER,
                reaction_type=ReactionType.LIKE,
            ),
            Reaction.create(
                comment_id=saved_comment.id,
                author_id=uuid4(),
                author_role=UserRole.SUPPORT_AGENT,
                reaction_type=ReactionType.IMPORTANT,
            ),
        ]
        for reaction in reactions:
            await reaction_repo.create(reaction)
        await session.commit()

        stats = await reaction_repo.get_reaction_stats(
            comment_ids=[saved_comment.id],
            user_id=user_id,
        )

        assert stats.counts[saved_comment.id][ReactionType.LIKE] == 2
        assert stats.counts[saved_comment.id][ReactionType.IMPORTANT] == 1
        assert stats.user_reactions[saved_comment.id] == {ReactionType.LIKE}
