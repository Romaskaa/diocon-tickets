from uuid import uuid4

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import CounterpartyType, Inn, Kpp, Phone
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.services import create_customer, create_support
from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import Project
from src.projects.domain.services import ProjectAccessService
from src.projects.domain.vo import ProjectRole
from src.shared.domain.exceptions import NotFoundError
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import Priority, TicketNumber, TicketStatus, TicketType
from src.tickets.schemas import TicketCreate, TicketEdit, TicketResponse
from src.tickets.services import TicketService


@pytest.fixture
def project_access_service(fake_membership_repo):
    return ProjectAccessService(fake_membership_repo)


@pytest.fixture
def ticket_service(
        mock_session,
        fake_ticket_repo,
        fake_project_repo,
        project_access_service,
        fake_counterparty_repo,
        fake_user_repo,
        event_publisher,
):
    return TicketService(
        session=mock_session,
        ticket_repo=fake_ticket_repo,
        project_repo=fake_project_repo,
        project_access_service=project_access_service,
        user_repo=fake_user_repo,
        counterparty_repo=fake_counterparty_repo,
        event_publisher=event_publisher,
    )


# =================== Проекты и контрагенты ===================


@pytest.fixture
def counterparty_id():
    return uuid4()


@pytest.fixture
async def created_counterparty(fake_counterparty_repo):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="Тест",
        legal_name="ООО Тест",
        inn=Inn("7707083893"),
        kpp=Kpp("770701001"),
        phone=Phone("88005553535"),
        email="test@mail.com",
    )
    await fake_counterparty_repo.create(counterparty)
    return counterparty


@pytest.fixture
async def created_project(counterparty_id, fake_project_repo):
    project = Project.create(
        name="Test project",
        key="TESTPRJ",
        created_by=uuid4(),
        counterparty_id=counterparty_id,
    )
    await fake_project_repo.create(project)
    return project


@pytest.fixture
async def created_ticket(fake_ticket_repo, current_support_agent):
    ticket = Ticket.create(
        ticket_number=TicketNumber("TEST-26-00000001"),
        title="Test ticket",
        description="This ticket created for test",
        reporter_id=current_support_agent.user_id,
        created_by=current_support_agent.user_id,
        created_by_role=current_support_agent.role,
    )
    await fake_ticket_repo.create(ticket)
    return ticket


@pytest.fixture
async def ticket_in_open(fake_ticket_repo, counterparty_id):
    ticket = Ticket(
        number=TicketNumber("TEST-26-00000001"),
        title="Test ticket",
        description="Opened ticket",
        type=TicketType.SERVICE_REQUEST,
        status=TicketStatus.OPEN,
        priority=Priority.MEDIUM,
        reporter_id=uuid4(),
        created_by=uuid4(),
        created_by_role=UserRole.CUSTOMER,
        counterparty_id=counterparty_id,
    )
    await fake_ticket_repo.create(ticket)
    return ticket


@pytest.fixture
async def opened_ticket_in_project(fake_ticket_repo, created_project):
    ticket = Ticket(
        number=TicketNumber("TEST-26-00000001"),
        title="Test ticket",
        description="Opened ticket",
        type=TicketType.SERVICE_REQUEST,
        status=TicketStatus.OPEN,
        priority=Priority.MEDIUM,
        reporter_id=uuid4(),
        created_by=uuid4(),
        created_by_role=UserRole.CUSTOMER,
        project_id=created_project.id,
        counterparty_id=uuid4(),
    )
    await fake_ticket_repo.create(ticket)
    return ticket


@pytest.fixture
async def created_support_agent(fake_user_repo):
    support_agent = create_support(
        email="support.agent@mail.ru",
        password_hash="1234567890",  # noqa: S106
        user_role=UserRole.SUPPORT_AGENT,
    )
    await fake_user_repo.create(support_agent)
    return support_agent


@pytest.fixture
async def created_customer(fake_user_repo, created_counterparty):
    customer = create_customer(
        email="customer@mail.ru",
        password_hash="1234567890",  # noqa: S106
        user_role=UserRole.CUSTOMER,
        counterparty_id=created_counterparty.id,
    )
    await fake_user_repo.create(customer)
    return customer


# =================== Пользователи с разными ролями ===================


@pytest.fixture
def current_support_agent(created_support_agent):
    return CurrentUser(
        user_id=created_support_agent.id,
        email=created_support_agent.email,
        role=created_support_agent.role,
    )


@pytest.fixture
def current_customer(created_customer):
    return CurrentUser(
        user_id=created_customer.id,
        email=created_customer.email,
        role=created_customer.role,
        counterparty_id=created_customer.counterparty_id,
    )


class TestCreate:
    """
    Тестирование создания тикета
    """

    @pytest.mark.asyncio
    async def test_create_without_project_and_counterparty_success(
            self, ticket_service, current_support_agent, mock_session, fake_ticket_repo
    ):
        """
        Успешное создание тикета вне проекта или контрагента
        """

        data = TicketCreate(
            title="Test ticket",
            description="This ticket created for test",
            type=TicketType.SERVICE_REQUEST,
            priority=Priority.MEDIUM,
            reporter_id=current_support_agent.user_id,
        )
        response = await ticket_service.create(data, current_support_agent)

        assert isinstance(response, TicketResponse)
        assert response.title == "Test ticket"
        assert response.number == "INT-26-00000001"

        mock_session.commit.assert_awaited_once()

        created_ticket = await fake_ticket_repo.read(response.id)
        assert created_ticket is not None
        assert response.number == created_ticket.number.value

    @pytest.mark.asyncio
    async def test_create_with_project_success(
            self, ticket_service, created_project, current_support_agent, fake_membership_repo
    ):
        """
        Успешное создание тикета внутри проекта
        """

        # Добавление агента поддержки в проект
        membership = created_project.create_membership(
            user_id=current_support_agent.user_id,
            project_role=ProjectRole.CONTRIBUTOR,
            created_by=uuid4(),
        )
        await fake_membership_repo.create(membership)

        data = TicketCreate(
            title="Test ticket",
            description="This ticket created for test",
            type=TicketType.SERVICE_REQUEST,
            priority=Priority.MEDIUM,
            project_id=created_project.id,
            reporter_id=current_support_agent.user_id,
        )
        response = await ticket_service.create(data, current_support_agent)

        assert response.project_id == created_project.id
        assert response.counterparty_id == created_project.counterparty_id
        assert response.number == "TESTPRJ-26-00000001"

    @pytest.mark.asyncio
    async def test_create_with_counterparty_success(
            self, ticket_service, created_counterparty, current_customer
    ):
        """
        Успешное создание тикета от контрагента
        """

        data = TicketCreate(
            title="Test ticket",
            description="This ticket created for test",
            type=TicketType.SERVICE_REQUEST,
            priority=Priority.MEDIUM,
            counterparty_id=created_counterparty.id,
            reporter_id=current_customer.user_id,
        )
        response = await ticket_service.create(data, current_customer)

        assert response.counterparty_id == created_counterparty.id
        assert response.number == "TEST-26-00000001"

    @pytest.mark.asyncio
    async def test_denied_by_project_access(
            self, ticket_service, created_project, current_support_agent
    ):
        """
        Запрет на создание тикета при отсутствии членства в проекте
        """

        data = TicketCreate(
            title="Test ticket",
            description="This ticket created for test",
            type=TicketType.SERVICE_REQUEST,
            priority=Priority.MEDIUM,
            project_id=created_project.id,
            reporter_id=current_support_agent.user_id,
        )

        with pytest.raises(PermissionDeniedError):
            await ticket_service.create(data, current_support_agent)

    @pytest.mark.asyncio
    async def test_creation_failed_when_project_not_found(
            self, ticket_service, current_support_agent
    ):
        """
        Нельзя создать тикет в проекте, если проект не создан
        """

        data = TicketCreate(
            title="Test ticket",
            description="This ticket created for test",
            type=TicketType.SERVICE_REQUEST,
            priority=Priority.MEDIUM,
            project_id=uuid4(),
            reporter_id=uuid4(),
        )

        with pytest.raises(NotFoundError, match=f"Project with ID {data.project_id} not found"):
            await ticket_service.create(data, current_support_agent)

    @pytest.mark.asyncio
    async def test_creation_failed_when_counterparty_not_found(
            self, ticket_service, current_support_agent
    ):
        """
        Нельзя создать тикет на контрагента, когда контрагент не создан
        """

        data = TicketCreate(
            title="Test ticket",
            description="This ticket created for test",
            type=TicketType.SERVICE_REQUEST,
            priority=Priority.MEDIUM,
            counterparty_id=uuid4(),
            reporter_id=uuid4(),
        )

        with pytest.raises(
                NotFoundError, match=f"Counterparty with ID {data.counterparty_id} not found"
        ):
            await ticket_service.create(data, current_support_agent)


class TestEdit:

    @pytest.mark.asyncio
    async def test_edit_success(
            self,
            ticket_service,
            fake_ticket_repo,
            current_support_agent,
            created_ticket,
            mock_session,
    ):
        """
        Успешное редактирование тикета
        """

        data = TicketEdit(title="New title")
        response = await ticket_service.edit(
            ticket_id=created_ticket.id,
            data=data,
            edited_by=current_support_agent.user_id,
        )

        assert response.title == "New title"

        mock_session.commit.assert_awaited_once()

        edited_ticket = await fake_ticket_repo.read(response.id)
        assert edited_ticket is not None
        assert edited_ticket.title == "New title"

    @pytest.mark.asyncio
    async def test_edit_failure_when_ticket_not_found(
            self, ticket_service, current_support_agent
    ):
        """
        Нельзя отредактировать несуществующий тикет
        """

        ticket_id = uuid4()
        data = TicketEdit(title="New title")

        with pytest.raises(NotFoundError, match=f"Ticket with ID {ticket_id} not found"):
            await ticket_service.edit(
                ticket_id=ticket_id,
                data=data,
                edited_by=current_support_agent.user_id,
            )


class TestArchive:

    @pytest.mark.asyncio
    async def test_archive_success(
            self,
            ticket_service,
            created_ticket,
            current_support_agent,
            fake_ticket_repo,
            mock_session,
    ):
        """
        Успешная архивация тикета
        """

        response = await ticket_service.archive(
            ticket_id=created_ticket.id, current_user=current_support_agent
        )

        assert response.is_archived is True

        mock_session.commit.assert_awaited_once()

        archived_ticket = await fake_ticket_repo.read(response.id)
        assert archived_ticket.is_deleted is True

    @pytest.mark.asyncio
    async def test_archive_denied(self, ticket_service, created_ticket, current_customer):
        """
        Пользователь не может архивировать чужие тикеты (кроме менеджера и админа)
        """

        with pytest.raises(PermissionDeniedError):
            await ticket_service.archive(
                ticket_id=created_ticket.id, current_user=current_customer
            )

    @pytest.mark.asyncio
    async def test_archive_failure_when_ticket_not_found(
            self, ticket_service, current_support_agent
    ):
        """
        Нельзя архивировать несуществующий тикет
        """

        ticket_id = uuid4()

        with pytest.raises(NotFoundError, match=f"Ticket with ID {ticket_id} not found"):
            await ticket_service.archive(ticket_id=ticket_id, current_user=current_support_agent)


class TestAssignTo:

    @pytest.mark.asyncio
    async def test_assign_to_success(
            self,
            ticket_service,
            ticket_in_open,
            fake_ticket_repo,
            current_support_agent,
            mock_session,
    ):
        """
        Успешное назначение исполнителя на тикет
        """

        response = await ticket_service.assign_to(
            ticket_id=ticket_in_open.id,
            assignee_id=current_support_agent.user_id,
            current_user=current_support_agent,
        )

        assert response.assignee_id == current_support_agent.user_id

        mock_session.commit.assert_awaited_once()

        assigned_ticket = await fake_ticket_repo.read(response.id)
        assert assigned_ticket.assignee_id == current_support_agent.user_id

    @pytest.mark.asyncio
    async def test_assign_with_project_check(
            self,
            ticket_service,
            opened_ticket_in_project,
            created_project,
            current_support_agent,
            fake_membership_repo,
    ):
        """
        Успешное назначение тикета в проекте
        """

        # Создание членства в проекте
        membership = created_project.create_membership(
            user_id=current_support_agent.user_id,
            project_role=ProjectRole.CONTRIBUTOR,
            created_by=uuid4(),
        )
        await fake_membership_repo.create(membership)

        response = await ticket_service.assign_to(
            ticket_id=opened_ticket_in_project.id,
            assignee_id=current_support_agent.user_id,
            current_user=current_support_agent,
        )

        assert response.assignee_id == current_support_agent.user_id

    @pytest.mark.asyncio
    async def test_assign_denied(
            self,
            ticket_service,
            ticket_in_open,
            current_customer,
            current_support_agent,
    ):
        """
        Нельзя назначить тикет на клиента
        """

        with pytest.raises(PermissionDeniedError):
            await ticket_service.assign_to(
                ticket_id=ticket_in_open.id,
                assignee_id=current_customer.user_id,
                current_user=current_support_agent,
            )

    @pytest.mark.asyncio
    async def test_assign_project_permission_denied(
            self,
            ticket_service,
            opened_ticket_in_project,
            created_project,
            current_customer,
            current_support_agent,
            fake_membership_repo,
    ):
        """
        Тест ошибки авторизации в проекте
        """

        # Создание членства в проекте
        contributor = created_project.create_membership(
            user_id=current_support_agent.user_id,
            project_role=ProjectRole.CONTRIBUTOR,
            created_by=uuid4(),
        )
        await fake_membership_repo.create(contributor)

        customer = created_project.create_membership(
            user_id=current_customer.user_id,
            project_role=ProjectRole.CUSTOMER,
            created_by=uuid4(),
        )
        await fake_membership_repo.create(customer)

        with pytest.raises(PermissionDeniedError):
            await ticket_service.assign_to(
                ticket_id=opened_ticket_in_project.id,
                assignee_id=current_customer.user_id,
                current_user=current_support_agent,
            )

    @pytest.mark.asyncio
    async def test_failure_when_ticket_not_found(self, ticket_service, current_support_agent):
        """
        Нельзя назначить исполнителя на несуществующий тикет
        """

        ticket_id = uuid4()
        with pytest.raises(NotFoundError, match=f"Ticket with ID {ticket_id} not found"):
            await ticket_service.assign_to(
                ticket_id=ticket_id,
                assignee_id=current_support_agent.user_id,
                current_user=current_support_agent,
            )

    @pytest.mark.asyncio
    async def test_assign_failure_when_user_not_found(
            self, ticket_service, current_support_agent, ticket_in_open,
    ):
        """
        Нельзя назначить тикет на несуществующего пользователя
        """

        assignee_id = uuid4()

        with pytest.raises(NotFoundError, match=f"User with ID {assignee_id} not found"):
            await ticket_service.assign_to(
                ticket_id=ticket_in_open.id,
                assignee_id=assignee_id,
                current_user=current_support_agent,
            )


class TestChangeStatus:

    @pytest.mark.asyncio
    async def test_change_status_success(
            self,
            ticket_service,
            ticket_in_open,
            current_support_agent,
            fake_ticket_repo,
            mock_session,
    ):
        """
        Успешное изменение статуса тикета
        """

        new_status = TicketStatus.IN_PROGRESS
        response = await ticket_service.change_status(
            ticket_id=ticket_in_open.id,
            new_status=new_status,
            current_user=current_support_agent,
        )

        assert response.status == new_status

        mock_session.commit.assert_awaited_once()

        changed_ticket = await fake_ticket_repo.read(response.id)
        assert changed_ticket.status == new_status

    @pytest.mark.asyncio
    async def test_change_status_with_project_check(
            self,
            ticket_service,
            opened_ticket_in_project,
            current_support_agent,
            created_project,
            fake_membership_repo,
    ):
        """
        Успешное изменение статуса для тикета внутри проекта
        """

        # Создание членства в проекте
        contributor = created_project.create_membership(
            user_id=current_support_agent.user_id,
            project_role=ProjectRole.CONTRIBUTOR,
            created_by=uuid4(),
        )
        await fake_membership_repo.create(contributor)

        new_status = TicketStatus.IN_PROGRESS
        response = await ticket_service.change_status(
            ticket_id=opened_ticket_in_project.id,
            new_status=new_status,
            current_user=current_support_agent,
        )

        assert response.status == new_status

    @pytest.mark.asyncio
    async def test_change_status_denied(
            self, ticket_service, ticket_in_open, current_customer
    ):
        """
        Тест ошибки авторизации при смене статуса
        """

        with pytest.raises(PermissionDeniedError):
            await ticket_service.change_status(
                ticket_id=ticket_in_open.id,
                new_status=TicketStatus.IN_PROGRESS,
                current_user=current_customer,
            )

    @pytest.mark.asyncio
    async def test_change_status_for_project_ticket_denied(
            self, ticket_service, opened_ticket_in_project, current_support_agent
    ):
        """
        Ошибка авторизации при смене статуса в проекте
        """

        with pytest.raises(PermissionDeniedError):
            await ticket_service.change_status(
                ticket_id=opened_ticket_in_project.id,
                new_status=TicketStatus.IN_PROGRESS,
                current_user=current_support_agent,
            )

    @pytest.mark.asyncio
    async def test_change_status_failure_when_ticket_not_found(
            self, ticket_service, current_support_agent
    ):
        """
        Нельзя сменить статус для несуществующего тикета
        """

        ticket_id = uuid4()

        with pytest.raises(NotFoundError, match=f"Ticket with ID {ticket_id} not found"):
            await ticket_service.change_status(
                ticket_id=ticket_id,
                new_status=TicketStatus.IN_PROGRESS,
                current_user=current_support_agent,
            )
