from uuid import uuid4

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import CounterpartyType, Inn, Kpp, Phone
from src.crm.infra.repos import SqlCounterpartyRepository
from src.iam.domain.vo import UserRole
from src.projects.domain.entities import Project
from src.projects.infra.repos import SqlProjectRepository
from src.shared.schemas import Pagination
from src.shared.utils.time import current_datetime
from src.tickets.domain.entities import Comment, Reaction, Ticket
from src.tickets.domain.vo import (
    CommentType,
    ReactionType,
    Tag,
    TicketNumber,
    Priority,
    TicketStatus,
)
from src.tickets.infra.repos import (
    SqlCommentRepository,
    SqlReactionRepository,
    SqlTicketRepository,
)
from src.tickets.domain.repos import TicketFilters
from src.tickets.domain.services import TicketScopes

EXPECTED_LIKE_REACTIONS_COUNT = 2


@pytest.fixture
def counterparty_repo(session):
    return SqlCounterpartyRepository(session)


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
        priority=Priority.HIGH,
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


def make_counterparty() -> Counterparty:
    return Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name=f"Scope Counterparty {uuid4()}",
        legal_name=f"Scope Legal Counterparty {uuid4()}",
        inn=Inn(f"{uuid4().int % 10**10:010d}"),
        kpp=Kpp(f"{uuid4().int % 10**9:09d}"),
        phone=Phone("+70000000000"),
        email=f"scope-counterparty-{uuid4()}@example.com",
        contact_persons=[],
        is_active=True,
    )


def make_scoped_ticket(*, reporter_id=None, project_id=None, counterparty_id=None) -> Ticket:
    creator_id = uuid4()

    return Ticket.create(
        ticket_number=TicketNumber(f"SCP-26-{uuid4().int % 10**8:08d}"),
        reporter_id=reporter_id or creator_id,
        created_by=creator_id,
        created_by_role=UserRole.ADMIN,
        title=f"Scoped ticket {uuid4()}",
        description="Ticket for scope filtering integration test",
        priority=Priority.HIGH,
        project_id=project_id,
        counterparty_id=counterparty_id,
        tags=[Tag(name="scope", color="#3498db")],
    )

@pytest.mark.integration
class TestSqlProjectRepository:
    @pytest.mark.asyncio
    async def test_get_by_key_returns_project(
            self, project_repo, saved_project
    ):
        """
        Репозиторий возвращает проект по ключу.
        Это основной поиск для сервисов проектов и проверки прав.
        """

        found_project = await project_repo.get_by_key(saved_project.key)

        assert found_project is not None
        assert found_project.id == saved_project.id
        assert found_project.key == saved_project.key
        assert found_project.owner_id == saved_project.owner_id


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
            pagination=Pagination(page=1, size=10),
            scopes=TicketScopes(),
            filters=TicketFilters(
                status=TicketStatus.NEW,
                priority=Priority.HIGH,
                tags=["integration"],
            ),
        )

        found_ids = {ticket.id for ticket in page.items}
        assert saved_ticket.id in found_ids
        assert all(ticket.status == TicketStatus.NEW for ticket in page.items)
        assert all(ticket.priority == Priority.HIGH for ticket in page.items)


    @pytest.mark.asyncio
    async def test_paginate_reporter_scope_returns_only_reporter_tickets(self, session, ticket_repo):
        """
        Проверяем reporter scope: репозиторий должен вернуть только тикеты,
        в которых указанный пользователь является инициатором.
        Данные: два тикета разных инициаторов в реальной БД.
        """

        reporter_id = uuid4()
        reporter_ticket = make_scoped_ticket(reporter_id=reporter_id)
        other_ticket = make_scoped_ticket(reporter_id=uuid4())

        await ticket_repo.create(reporter_ticket)
        await ticket_repo.create(other_ticket)
        await session.commit()

        page = await ticket_repo.paginate(
            pagination=Pagination(page=1, size=100),
            scopes=TicketScopes(reporter_id=reporter_id),
        )

        found_ids = {ticket.id for ticket in page.items}

        assert reporter_ticket.id in found_ids
        assert other_ticket.id not in found_ids
        assert all(
            ticket.reporter_id == reporter_id
            for ticket in page.items
        )


    @pytest.mark.asyncio
    async def test_paginate_counterparty_scope_returns_counterparty_and_project_tickets(
        self,
        session,
        counterparty_repo,
        project_repo,
        ticket_repo,
    ):
        """
        Проверяем counterparty scope: должны возвращаться прямые тикеты
        контрагента и тикеты его доступных проектов.
        Данные: два контрагента, два проекта и тикеты разных контекстов.
        """

        counterparty = make_counterparty()
        other_counterparty = make_counterparty()

        await counterparty_repo.create(counterparty)
        await counterparty_repo.create(other_counterparty)
        await session.commit()

        counterparty_id = counterparty.id
        other_counterparty_id = other_counterparty.id

        accessible_project = Project.create(
            name=f"Accessible project {uuid4()}",
            key=f"AC{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
            counterparty_id=counterparty_id,
        )
        other_project = Project.create(
            name=f"Other project {uuid4()}",
            key=f"OT{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
            counterparty_id=other_counterparty_id,
        )

        await project_repo.create(accessible_project)
        await project_repo.create(other_project)

        direct_ticket = make_scoped_ticket(counterparty_id=counterparty_id)
        project_ticket = make_scoped_ticket(
            project_id=accessible_project.id,
            counterparty_id=counterparty_id,
        )
        other_counterparty_ticket = make_scoped_ticket(counterparty_id=other_counterparty_id)
        other_project_ticket = make_scoped_ticket(
            project_id=other_project.id,
            counterparty_id=other_counterparty_id,
        )

        for ticket in (direct_ticket, project_ticket, other_counterparty_ticket, other_project_ticket):
            await ticket_repo.create(ticket)
        
        await session.commit()

        page = await ticket_repo.paginate(
            pagination=Pagination(page=1, size=100),
            scopes=TicketScopes(
                counterparty_id=counterparty_id,
                project_ids=[accessible_project.id]
            ),
        )

        found_ids = {ticket.id for ticket in page.items}

        assert direct_ticket.id in found_ids
        assert project_ticket.id in found_ids
        assert other_counterparty_ticket.id not in found_ids
        assert other_project_ticket.id not in found_ids

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
            priority=Priority.HIGH,
        )
        await ticket_repo.create(other_ticket)
        await session.commit()

        page = await ticket_repo.get_by_reporter(
            reporter_id=saved_ticket.reporter_id,
            params=Pagination(page=1, size=10),
        )

        found_ids = {ticket.id for ticket in page.items}
        assert saved_ticket.id in found_ids
        assert other_ticket.id not in found_ids
        assert all(ticket.reporter_id == saved_ticket.reporter_id for ticket in page.items)

    
    @pytest.mark.asyncio
    async def test_paginate_project_scope_returns_internal_and_accessible_project_tickets(self, session, project_repo, ticket_repo):
        """
        Проверяем project scope: репозиторий должен вернуть внутренние тикеты
        и тикеты доступного проекта, но скрыть тикеты других проектов.
        Данные: внутренний тикет и тикеты двух разных проектов в реальной БД.
        """

        accessible_project = Project.create(
            name=f"Accessible support project {uuid4()}",
            key=f"AP{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
        )
        inaccessible_project = Project.create(
            name=f"Inaccessible support project {uuid4()}",
            key=f"IP{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
        )

        await project_repo.create(accessible_project)
        await project_repo.create(inaccessible_project)
        await session.commit()

        internal_ticket = make_scoped_ticket()
        accessible_ticket = make_scoped_ticket(project_id=accessible_project.id)
        inaccessible_ticket = make_scoped_ticket(project_id=inaccessible_project.id)

        await ticket_repo.create(internal_ticket)
        await ticket_repo.create(accessible_ticket)
        await ticket_repo.create(inaccessible_ticket)
        await session.commit()

        page = await ticket_repo.paginate(
            pagination=Pagination(page=1, size=100),
            scopes=TicketScopes(project_ids=[accessible_project.id]),
        )

        found_ids =  {ticket.id for ticket in page.items}

        assert internal_ticket.id in found_ids
        assert accessible_ticket.id in found_ids
        assert inaccessible_ticket.id not in found_ids


    @pytest.mark.asyncio
    async def test_paginate_empty_project_scope_returns_only_internal_tickets(self, session, project_repo, ticket_repo):
        """
        Проверяем пустой project scope: пользователь без доступных проектов
        должен видеть только внутренние тикеты без project_id.
        Данные: внутренний тикет и тикет существующего проекта в реальной БД.
        """

        unavailable_project = Project.create(
            name=f"Unavailable project {uuid4()}",
            key=f"UP{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
        )

        await project_repo.create(unavailable_project)
        await session.commit()

        internal_ticket = make_scoped_ticket()
        project_ticket = make_scoped_ticket(project_id=unavailable_project.id)

        await ticket_repo.create(internal_ticket)
        await ticket_repo.create(project_ticket)
        await session.commit()

        page = await ticket_repo.paginate(
            pagination=Pagination(page=1, size=100),
            scopes=TicketScopes(project_ids=[]),
        )

        found_ids = {ticket.id for ticket in page.items}

        assert internal_ticket.id in found_ids
        assert project_ticket.id not in found_ids
        assert all(ticket.project_id is None for ticket in page.items)


    @pytest.mark.asyncio
    async def test_get_total_counts_only_internal_tickets(self, session, ticket_repo):
        """
        Проверяем get_total для внутренних тикетов: репозиторий должен учитывать
        только тикеты без project_id и counterparty_id.
        Данные: два внутренних тикета и тикет контрагента в реальной БД.
        """

        total_before = await ticket_repo.get_total()

        first_internal_ticket = make_scoped_ticket()
        second_internal_ticket = make_scoped_ticket()
        counterparty_ticket = make_scoped_ticket(counterparty_id=uuid4())

        await ticket_repo.create(first_internal_ticket)
        await ticket_repo.create(second_internal_ticket)
        await ticket_repo.create(counterparty_ticket)
        await session.commit()

        total = await ticket_repo.get_total()

        assert total == total_before + 2


    @pytest.mark.asyncio
    async def test_get_total_counts_counterparty_tickets_without_project(self, session, counterparty_repo, project_repo, ticket_repo):
        """
        Проверяем get_total для контрагента: репозиторий должен учитывать только
        прямые тикеты контрагента бещ привязки и проекту.
        Данные: два прямых тикета контрагента и один проектный тикет.
        """

        counterparty = make_counterparty()

        await counterparty_repo.create(counterparty)
        await session.commit()

        project = Project.create(
            name=f"Counterparty project {uuid4()}",
            key=f"CP{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
            counterparty_id=counterparty.id,
        )

        await project_repo.create(project)
        await session.commit()

        first_direct_ticket = make_scoped_ticket(counterparty_id=counterparty.id)
        second_direct_ticket = make_scoped_ticket(counterparty_id=counterparty.id)
        project_ticket = make_scoped_ticket(
            project_id=project.id,
            counterparty_id=counterparty.id,
        )

        await ticket_repo.create(first_direct_ticket)
        await ticket_repo.create(second_direct_ticket)
        await ticket_repo.create(project_ticket)
        await session.commit()

        total = await ticket_repo.get_total(counterparty_id=counterparty.id)

        assert total == 2


    @pytest.mark.asyncio
    async def test_get_total_counts_only_selected_project_tickets(self, session, project_repo, ticket_repo):
        """
        Проверяем get_total для проекта: репозиторий должен учитывать только
        тикеты выбранного проекта.
        Данные: два тикета выбранного проекта, тикет другого проекта
        и внутренний тикет в реальной БД.
        """

        selected_project = Project.create(
            name=f"Selected project {uuid4()}",
            key=f"SP{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
        )
        other_project = Project.create(
            name=f"Other project {uuid4()}",
            key=f"OP{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
        )

        await project_repo.create(selected_project)
        await project_repo.create(other_project)
        await session.commit()

        first_selected_ticket = make_scoped_ticket(
            project_id=selected_project.id,
        )
        second_selected_ticket = make_scoped_ticket(
            project_id=selected_project.id,
        )
        other_project_ticket = make_scoped_ticket(
            project_id=other_project.id,
        )
        internal_ticket = make_scoped_ticket()

        await ticket_repo.create(first_selected_ticket)
        await ticket_repo.create(second_selected_ticket)
        await ticket_repo.create(other_project_ticket)
        await ticket_repo.create(internal_ticket)
        await session.commit()

        total = await ticket_repo.get_total(
            project_id=selected_project.id,
        )

        assert total == 2


    @pytest.mark.asyncio
    async def test_get_by_ticket_returns_only_current_user_notes(self, session, comment_repo, saved_ticket):
        """
        Проверяем видимость корневых NOTE-комментариев: пользователь должен 
        видеть собственные заметки, но не заметки другого пользователя.
        Данные: публичный комментрий и две заметки разных авторов.
        """

        current_user_id = uuid4()
        other_user_id = uuid4()

        public_comment = Comment.create(
            ticket_id=saved_ticket.id,
            author_id=other_user_id,
            author_role=UserRole.SUPPORT_AGENT,
            text="Public comment",
            comment_type=CommentType.PUBLIC,
        )
        current_user_note = Comment.create(
            ticket_id=saved_ticket.id,
            author_id=current_user_id,
            author_role=UserRole.SUPPORT_AGENT,
            text="Current user private note",
            comment_type=CommentType.NOTE,
        )
        other_user_note = Comment.create(
            ticket_id=saved_ticket.id,
            author_id=other_user_id,
            author_role=UserRole.SUPPORT_AGENT,
            text="Other user private note",
            comment_type=CommentType.NOTE,
        )

        await comment_repo.create(public_comment)
        await comment_repo.create(current_user_note)
        await comment_repo.create(other_user_note)
        await session.commit()

        page = await comment_repo.get_by_ticket(
            ticket_id=saved_ticket.id,
            pagination=Pagination(page=1, size=100),
            user_id=current_user_id,
            include_notes=True,
        )

        found_ids = {comment.id for comment in page.items}

        assert public_comment.id in found_ids
        assert current_user_note.id in found_ids
        assert other_user_note.id not in found_ids


    @pytest.mark.asyncio
    async def test_get_replies_returns_only_current_user_notes(self, session, comment_repo, saved_comment):
        """
        Проверяем видимость NOTE-ответов: пользователь должен видеть
        собственную заметку, но не заметку другого пользователя.
        Данные: публичный reply и два NOTE-reply разных авторов.
        """

        current_user_id = uuid4()
        other_user_id = uuid4()

        public_reply = saved_comment.create_reply(
            author_id=other_user_id,
            author_role=UserRole.SUPPORT_AGENT,
            text="Public reply",
            comment_type=CommentType.PUBLIC,
        )
        current_user_note = saved_comment.create_reply(
            author_id=current_user_id,
            author_role=UserRole.SUPPORT_AGENT,
            text="Current user private reply note",
            comment_type=CommentType.NOTE,
        )
        other_user_note = saved_comment.create_reply(
            author_id=other_user_id,
            author_role=UserRole.SUPPORT_AGENT,
            text="Other user private reply note",
            comment_type=CommentType.NOTE,
        )

        await comment_repo.create(public_reply)
        await comment_repo.create(current_user_note)
        await comment_repo.create(other_user_note)
        await session.commit()

        page = await comment_repo.get_replies(
            parent_comment_id=saved_comment.id,
            pagination=Pagination(page=1, size=100),
            user_id=current_user_id,
            include_notes=True,
        )

        found_ids = {comment.id for comment in page.items}

        assert public_reply.id in found_ids
        assert current_user_note.id in found_ids
        assert other_user_note.id not in found_ids


    @pytest.mark.asyncio
    async def test_paginate_applies_full_text_search(self, session, ticket_repo):
        """
        Проверяем полнотекстовый поиск PostgreSQL: репозиторий должен вернуть
        тикет, содержащий поисковое слово в заголовке или описании.
        Данные: подходящий и неподходящий тикеты в реальной БД.
        """

        matching_ticket = Ticket.create(
            ticket_number=TicketNumber(f"SRCH-26-{uuid4().int % 10**8:08d}"),
            reporter_id=uuid4(),
            created_by=uuid4(),
            created_by_role=UserRole.ADMIN,
            title="Необходима калибровка промышленного принтера",
            description="Устройство печатает изображения с искажениями",
            priority=Priority.HIGH,
        )
        other_ticket = Ticket.create(
            ticket_number=TicketNumber(f"SRCH-26-{uuid4().int % 10**8:08d}"),
            reporter_id=uuid4(),
            created_by=uuid4(),
            created_by_role=UserRole.ADMIN,
            title="Не работает корпоративная почта",
            description="Пользователь не может отправить письмо",
            priority=Priority.HIGH,
        )

        await ticket_repo.create(matching_ticket)
        await ticket_repo.create(other_ticket)
        await session.commit()

        page = await ticket_repo.paginate(
            pagination=Pagination(page=1, size=100),
            scopes=TicketScopes(),
            filters=TicketFilters(query="калибровка"),
        )

        found_ids = {ticket.id for ticket in page.items}

        assert matching_ticket.id in found_ids
        assert other_ticket.id not in found_ids


    @pytest.mark.asyncio
    async def test_paginate_returns_empty_page_when_nothing_matches(self, ticket_repo):
        """
        Проверяем paginate: если ни один тикет не соответствует фильтрам,
        репозиторий должен вернуть корректную пустую страницу.
        Данные: уникальный поисковый запрос, отсутствующий в реальной БД.
        """

        page = await ticket_repo.paginate(
            pagination=Pagination(page=1, size=10),
            scopes=TicketScopes(),
            filters=TicketFilters(
                query=f"missingticketquery{uuid4().hex}",
            ),
        )

        assert page.items == []
        assert page.total_items == 0
        assert page.total_pages == 0
        assert page.has_next is False
        assert page.has_prev is False


    @pytest.mark.asyncio
    async def test_get_total_filters_by_project_and_counterparty(self, session, counterparty_repo, project_repo, ticket_repo):
        """
        Проверяем get_total с project_id и counterparty_id: репозиторий должен
        учитывать только тикеты, соответствующие обоим параметрам.
        Данные: тикеты разных проектов и контрагентов в реальной БД.
        """

        counterparty = make_counterparty()
        other_counterparty = make_counterparty()

        await counterparty_repo.create(counterparty)
        await counterparty_repo.create(other_counterparty)
        await session.commit()

        selected_project = Project.create(
            name=f"Selected counterparty project {uuid4()}",
            key=f"SC{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
            counterparty_id=counterparty.id,
        )
        other_project = Project.create(
            name=f"Other counterparty project {uuid4()}",
            key=f"OC{uuid4().hex[:6].upper()}",
            created_by=uuid4(),
            counterparty_id=counterparty.id,
        )

        await project_repo.create(selected_project)
        await project_repo.create(other_project)
        await session.commit()

        matching_ticket = make_scoped_ticket(
            project_id=selected_project.id,
            counterparty_id=counterparty.id,
        )
        wrong_counterparty_ticket = make_scoped_ticket(
            project_id=selected_project.id,
            counterparty_id=other_counterparty.id,
        )
        wrong_project_ticket = make_scoped_ticket(
            project_id=other_project.id,
            counterparty_id=counterparty.id,
        )

        await ticket_repo.create(matching_ticket)
        await ticket_repo.create(wrong_counterparty_ticket)
        await ticket_repo.create(wrong_project_ticket)
        await session.commit()

        total = await ticket_repo.get_total(
            project_id=selected_project.id,
            counterparty_id=counterparty.id,
        )

        assert total == 1


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
            pagination=Pagination(page=1, size=10),
        )
        internal_page = await comment_repo.get_by_ticket(
            ticket_id=saved_ticket.id,
            pagination=Pagination(page=1, size=10),
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
            pagination=Pagination(page=1, size=10),
        )
        internal_page = await comment_repo.get_replies(
            parent_comment_id=saved_comment.id,
            pagination=Pagination(page=1, size=10),
            include_internal=True,
        )

        public_ids = {item.id for item in public_page.items}
        internal_ids = {item.id for item in internal_page.items}

        assert public_reply.id in public_ids
        assert internal_reply.id not in public_ids
        assert internal_reply.id in internal_ids

    
    @pytest.mark.asyncio
    async def test_get_by_ticket_with_notes_without_user_id_raises_error(self, comment_repo, saved_ticket):
        """
        Проверяем get_by_ticket: при запросе личных NOTE-комментариев
        необходимо передать идентификатор текущего пользователя.
        Данные: существующий тикет, include_notes=True и user_id=None.
        """

        with pytest.raises(
            ValueError,
            match="User ID required for received NOTE comments",
        ):
            await comment_repo.get_by_ticket(
                ticket_id=saved_ticket.id,
                pagination=Pagination(page=1, size=10),
                include_notes=True,
            )


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

        assert stats.counts[saved_comment.id][ReactionType.LIKE] == EXPECTED_LIKE_REACTIONS_COUNT
        assert stats.counts[saved_comment.id][ReactionType.IMPORTANT] == 1
        assert stats.user_reactions[saved_comment.id] == {ReactionType.LIKE}


    @pytest.mark.asyncio
    async def test_get_reaction_stats_ignores_deleted_reactions(self, session, reaction_repo, saved_comment):
        """
        Проверяем статистику реакций: soft-deleted реакции не должны
        учитываться в общих счётчиках и реакциях текущего пользователя.
        Данные: активная LIKE и удалённая IMPORTANT одного пользователя.
        """

        user_id = uuid4()

        active_reaction = Reaction.create(
            comment_id=saved_comment.id,
            author_id=user_id,
            author_role=UserRole.SUPPORT_AGENT,
            reaction_type=ReactionType.LIKE,
        )
        deleted_reaction = Reaction.create(
            comment_id=saved_comment.id,
            author_id=user_id,
            author_role=UserRole.SUPPORT_AGENT,
            reaction_type=ReactionType.IMPORTANT,
        )

        await reaction_repo.create(active_reaction)
        await reaction_repo.create(deleted_reaction)
        await session.commit()

        await reaction_repo.update(
            deleted_reaction.id,
            deleted_at=current_datetime(),
        )
        await session.commit()

        stats = await reaction_repo.get_reaction_stats(
            comment_ids=[saved_comment.id],
            user_id=user_id,
        )

        assert stats.counts[saved_comment.id][ReactionType.LIKE] == 1
        assert ReactionType.IMPORTANT not in stats.counts[saved_comment.id]
        assert stats.user_reactions[saved_comment.id] == {
            ReactionType.LIKE,
        }
