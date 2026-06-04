from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import CounterpartyType, Inn, Kpp, Phone
from src.iam.dependencies import CurrentUser
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.services import create_customer, create_support
from src.iam.domain.vo import UserRole
from src.iam.security import hash_password
from src.shared.domain.exceptions import NotFoundError
from src.tickets.domain.entities import Project, Ticket
from src.tickets.domain.vo import (
    ProjectRole,
    TicketNumber,
    TicketPriority,
    TicketStatus,
)
from src.tickets.schemas import Tag, TicketCreate, TicketEdit
from src.tickets.services import TicketService


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def ticket_service(
        mock_session,
        mock_ticket_repo,
        mock_project_repo,
        mock_counterparty_repo,
        mock_user_repo,
        event_publisher,
):
    return TicketService(
        session=mock_session,
        ticket_repo=mock_ticket_repo,
        project_repo=mock_project_repo,
        counterparty_repo=mock_counterparty_repo,
        user_repo=mock_user_repo,
        event_publisher=event_publisher,
    )


@pytest.fixture
async def sample_counterparty(mock_counterparty_repo):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        phone=Phone("+79991234567"),
        email="info@romashka.ru",
    )
    await mock_counterparty_repo.create(counterparty)
    return counterparty


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
async def sample_project(
        mock_project_repo,
        sample_counterparty,
        owner_id,
        user_id,
        support_agent_id,
):
    project = Project.create(
        name="Test Project",
        key="TEST",
        owner_id=owner_id,
        created_by=uuid4(),
        description="Test description",
        counterparty_id=sample_counterparty.id,
    )
    project.add_member(
        user_id=user_id,
        project_role=ProjectRole.MEMBER,
        added_by=owner_id,
        added_by_role=UserRole.CUSTOMER_ADMIN,
    )
    project.add_member(
        user_id=support_agent_id,
        project_role=ProjectRole.MANAGER,
        added_by=owner_id,
        added_by_role=UserRole.CUSTOMER_ADMIN,
    )
    await mock_project_repo.create(project)
    return project


@pytest.fixture
def reporter_id():
    return uuid4()


@pytest.fixture
def support_agent_id():
    return uuid4()


@pytest.fixture
def customer_admin_id():
    return uuid4()


@pytest.fixture
def sample_ticket_number():
    return TicketNumber(value="WEB-26-00000145")


@pytest.fixture
async def sample_ticket(reporter_id, support_agent_id, sample_ticket_number, mock_ticket_repo):
    ticket = Ticket.create(
        ticket_number=sample_ticket_number,
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        priority=TicketPriority.MEDIUM,
        counterparty_id=uuid4(),
    )
    await mock_ticket_repo.create(ticket)
    return ticket


@pytest.fixture
def ticket_in_open(reporter_id, support_agent_id, sample_ticket_number):
    ticket = Ticket.create(
        ticket_number=sample_ticket_number,
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        priority=TicketPriority.MEDIUM,
        counterparty_id=uuid4(),
    )
    ticket.status = TicketStatus.OPEN
    return ticket


@pytest.fixture
def ticket_in_progress(reporter_id, support_agent_id, sample_ticket_number):
    ticket = Ticket.create(
        ticket_number=sample_ticket_number,
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        priority=TicketPriority.HIGH,
        counterparty_id=uuid4(),
    )
    ticket.status = TicketStatus.IN_PROGRESS
    return ticket


@pytest.fixture
def ticket_in_counterparty(sample_counterparty, reporter_id, support_agent_id):
    return Ticket.create(
        ticket_number=TicketNumber("TEST-26-00000001"),
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Тестовое описание",
        priority=TicketPriority.HIGH,
        counterparty_id=sample_counterparty.id,
    )


@pytest.fixture
async def sample_support(mock_user_repo):
    support = create_support(
        email="support@example.com",
        password_hash=hash_password("1234567890"),
        user_role=UserRole.SUPPORT_AGENT,
        full_name="Иванов Иван Иванович"
    )
    await mock_user_repo.create(support)
    return support


@pytest.fixture
async def sample_customer(mock_user_repo, sample_counterparty):
    customer = create_customer(
        email="customer@example.com",
        password_hash=hash_password("1334567890"),
        counterparty_id=sample_counterparty.id,
        user_role=UserRole.CUSTOMER,
    )
    await mock_user_repo.create(customer)
    return customer


@pytest.fixture
def current_support_user():
    return CurrentUser(
        user_id=uuid4(),
        email="support@example.com",
        role=UserRole.SUPPORT_AGENT,
    )


@pytest.fixture
def current_customer_user(sample_counterparty):
    return CurrentUser(
        user_id=uuid4(),
        email="customer@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=sample_counterparty.id,
    )


@pytest.fixture
def current_customer_admin_user(sample_counterparty):
    return CurrentUser(
        user_id=uuid4(),
        email="customer.admin@example.com",
        role=UserRole.CUSTOMER_ADMIN,
        counterparty_id=sample_counterparty.id,
    )


@pytest.fixture
def current_customer_reporter_user(sample_counterparty, ticket_in_open, reporter_id):
    return CurrentUser(
        user_id=reporter_id,
        email="customer.and.repoter.admin@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=sample_counterparty.id,
    )


class TestCreate:
    """
    Тестирование метода для создания тикета
    """

    @pytest.mark.asyncio
    async def test_create_internal_and_exists_success(
            self, ticket_service, mock_ticket_repo
    ):
        created_by = uuid4()
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Internal issue",
            description="Some description",
            priority=TicketPriority.MEDIUM,
            tags=[],
        )

        response = await ticket_service.create(data, created_by, UserRole.ADMIN)

        assert response.id is not None
        assert response.title == data.title
        assert response.project_id is None
        assert response.counterparty_id is None

        existing_ticket = await mock_ticket_repo.read(response.id)
        assert existing_ticket is not None
        assert existing_ticket.number.value.startswith("INT-")

    @pytest.mark.asyncio
    async def test_create_for_counterparty_success(
            self, ticket_service, sample_counterparty
    ):
        # 1. Формирование входных параметров
        created_by = uuid4()
        created_by_role = UserRole.SUPPORT_AGENT
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            counterparty_id=sample_counterparty.id,
        )

        # 2. Создание тикета
        response = await ticket_service.create(data, created_by, created_by_role)

        assert response.id is not None
        assert not response.number.startswith("INT-")
        assert response.number.startswith("OOOROMASHK-")
        assert response.counterparty_id == sample_counterparty.id
        assert response.project_id is None

    @pytest.mark.asyncio
    async def test_create_in_project_by_owner_success(
            self, ticket_service, sample_project, owner_id
    ):
        # 1. Формирование входных параметров
        created_by_role = UserRole.CUSTOMER_ADMIN
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=sample_project.id,
        )

        # 2. Создание тикета
        response = await ticket_service.create(data, owner_id, created_by_role)

        assert response.id is not None
        assert response.number.startswith(f"{sample_project.key}-")
        assert response.counterparty_id == sample_project.counterparty_id
        assert response.project_id == sample_project.id

    @pytest.mark.asyncio
    async def test_create_specify_project_and_counterparty_raises_error(
            self, ticket_service
    ):
        created_by = uuid4()
        created_by_role = UserRole.CUSTOMER_ADMIN
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=uuid4(),
            counterparty_id=uuid4(),
        )

        with pytest.raises(
                ValueError, match="Only one of the project or counterparty must be specified"
        ):
            await ticket_service.create(data, created_by, created_by_role)

    @pytest.mark.asyncio
    async def test_forbidden_create_in_project(self, ticket_service, sample_project):
        created_by = uuid4()
        created_by_role = UserRole.SUPPORT_AGENT
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=sample_project.id,
        )

        with pytest.raises(PermissionDeniedError):
            await ticket_service.create(data, created_by, created_by_role)

    @pytest.mark.asyncio
    async def test_create_raises_not_found(self, ticket_service):
        created_by = uuid4()
        created_by_role = UserRole.SUPPORT_AGENT
        in_project_data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=uuid4(),
        )

        with pytest.raises(NotFoundError):
            await ticket_service.create(in_project_data, created_by, created_by_role)

        for_counterparty_data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            counterparty_id=uuid4(),
        )

        with pytest.raises(NotFoundError):
            await ticket_service.create(for_counterparty_data, created_by, created_by_role)

    @pytest.mark.asyncio
    async def test_multiple_create_in_project_success(
            self, ticket_service, sample_project, owner_id
    ):
        created_by_role = UserRole.CUSTOMER_ADMIN

        data1 = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=sample_project.id,
        )
        data2 = TicketCreate(
            reporter_id=uuid4(),
            title="Не работает форма обратной связи",
            description="Не приходят сообщение на почту",
            priority=TicketPriority.CRITICAL,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=sample_project.id,
        )

        response1 = await ticket_service.create(data1, owner_id, created_by_role)
        response2 = await ticket_service.create(data2, owner_id, created_by_role)

        assert (
                response1.number.startswith(f"{sample_project.key}-")
                == response2.number.startswith(f"{sample_project.key}-")
        )
        assert response1.number.endswith("01")
        assert response2.number.endswith("02")

    @pytest.mark.asyncio
    async def test_multiple_create_for_counterparty_success(
        self, ticket_service, sample_counterparty
    ):
        created_by = uuid4()
        created_by_role = UserRole.CUSTOMER_ADMIN

        data1 = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            counterparty_id=sample_counterparty.id,
        )
        data2 = TicketCreate(
            reporter_id=uuid4(),
            title="Не работает форма обратной связи",
            description="Не приходят сообщение на почту",
            priority=TicketPriority.CRITICAL,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            counterparty_id=sample_counterparty.id,
        )

        response1 = await ticket_service.create(data1, created_by, created_by_role)
        response2 = await ticket_service.create(data2, created_by, created_by_role)

        assert response1.number[:5] == response2.number[:5]
        assert response1.number.endswith("01")
        assert response2.number.endswith("02")


class TestChangeStatus:
    """
    Тесты для изменения статуса тикета
    """

    @pytest.mark.asyncio
    async def test_change_status_success(self, ticket_service, mock_ticket_repo, sample_ticket):
        new_status = TicketStatus.OPEN

        response = await ticket_service.change_status(
            ticket_id=sample_ticket.id,
            new_status=new_status,
            changed_by=uuid4(),
            changed_by_role=UserRole.SUPPORT_AGENT,
        )

        assert response.status == new_status

        ticket = await mock_ticket_repo.read(sample_ticket.id)

        assert ticket is not None
        assert ticket.status == new_status

    @pytest.mark.asyncio
    async def test_change_status_ticket_not_found(self, ticket_service):

        with pytest.raises(NotFoundError):
            await ticket_service.change_status(
                ticket_id=uuid4(),
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid4(),
                changed_by_role=UserRole.SUPPORT_AGENT,
            )

    @pytest.mark.asyncio
    async def test_change_status_in_project_permission_check(
            self,
            owner_id,
            user_id,
            ticket_service,
            sample_ticket,
            sample_project,
    ):
        created_by_role = UserRole.CUSTOMER_ADMIN
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=sample_project.id,
        )

        await ticket_service.create(data, owner_id, created_by_role)

        response = await ticket_service.change_status(
            ticket_id=sample_ticket.id,
            new_status=TicketStatus.OPEN,
            changed_by=user_id,
            changed_by_role=UserRole.SUPPORT_AGENT,
        )

        assert response.status == TicketStatus.OPEN

    @pytest.mark.asyncio
    async def test_change_status_in_project_no_permission(
        self, user_id, ticket_service, sample_project, sample_ticket
    ):
        created_by_role = UserRole.CUSTOMER_ADMIN
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=sample_project.id,
        )

        await ticket_service.create(data, user_id, created_by_role)

        with pytest.raises(PermissionDeniedError):
            await ticket_service.change_status(
                ticket_id=sample_ticket.id,
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid4(),
                changed_by_role=UserRole.SUPPORT_AGENT,
            )

    @pytest.mark.asyncio
    async def test_customer_admin_can_approve_pending_approval(
        self, sample_ticket_number, ticket_service, mock_ticket_repo
    ):
        ticket = Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=uuid4(),
            created_by=uuid4(),
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Тестовый тикет",
            description="Описание",
            priority=TicketPriority.MEDIUM,
            counterparty_id=uuid4(),
        )
        ticket.status = TicketStatus.PENDING_APPROVAL
        await mock_ticket_repo.create(ticket)

        response = await ticket_service.change_status(
            ticket_id=ticket.id,
            new_status=TicketStatus.OPEN,
            changed_by=uuid4(),
            changed_by_role=UserRole.CUSTOMER_ADMIN,
        )

        assert response.id == ticket.id

    @pytest.mark.asyncio
    async def test_customer_admin_cannot_move_to_in_progress_from_pending(
        self, sample_ticket_number, ticket_service, mock_ticket_repo
    ):
        ticket = Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=uuid4(),
            created_by=uuid4(),
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Тестовый тикет",
            description="Описание",
            priority=TicketPriority.MEDIUM,
            counterparty_id=uuid4(),
        )
        ticket.status = TicketStatus.PENDING_APPROVAL
        await mock_ticket_repo.create(ticket)

        with pytest.raises(PermissionDeniedError):
            await ticket_service.change_status(
                ticket_id=ticket.id,
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid4(),
                changed_by_role=UserRole.CUSTOMER_ADMIN,
            )

    @pytest.mark.asyncio
    async def test_customer_can_only_reopen_closed_ticket(
            self, sample_ticket_number, ticket_service, mock_ticket_repo
    ):
        ticket = Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=uuid4(),
            created_by=uuid4(),
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Тестовый тикет",
            description="Описание",
            priority=TicketPriority.MEDIUM,
            counterparty_id=uuid4(),
        )
        ticket.status = TicketStatus.CLOSED
        await mock_ticket_repo.create(ticket)

        await ticket_service.change_status(
            ticket_id=ticket.id,
            new_status=TicketStatus.REOPENED,
            changed_by=uuid4(),
            changed_by_role=UserRole.CUSTOMER,
        )

        ticket.status = TicketStatus.OPEN
        await mock_ticket_repo.upsert(ticket)

        with pytest.raises(PermissionDeniedError):
            await ticket_service.change_status(
                ticket_id=ticket.id,
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid4(),
                changed_by_role=UserRole.CUSTOMER,
            )


class TestAssignTo:
    """
    Тест назначения тикета на исполнителя
    """

    @pytest.mark.asyncio
    async def test_assign_to_success(
            self,
            ticket_service,
            mock_ticket_repo,
            ticket_in_progress,
            support_agent_id,
            sample_support,
    ):
        """
        Успешное назначение тикета агентом поддержки
        """

        await mock_ticket_repo.create(ticket_in_progress)
        assignee_id = sample_support.id

        response = await ticket_service.assign_to(
            ticket_id=ticket_in_progress.id,
            assignee_id=assignee_id,
            assigned_by=support_agent_id,
            assigned_by_role=UserRole.SUPPORT_AGENT,
        )

        assert response.assigned_to == assignee_id

        existing_ticket = await mock_ticket_repo.read(ticket_in_progress.id)

        assert existing_ticket.assigned_to == assignee_id

    @pytest.mark.asyncio
    async def test_cannot_assign_to_customer(
            self,
            ticket_service,
            mock_ticket_repo,
            ticket_in_progress,
            support_agent_id,
            sample_customer,
    ):
        """
        Нельзя назначить тикет на клиента
        """

        await mock_ticket_repo.create(ticket_in_progress)
        assignee_id = sample_customer.id

        with pytest.raises(PermissionDeniedError):
            await ticket_service.assign_to(
                ticket_id=ticket_in_progress.id,
                assignee_id=assignee_id,
                assigned_by=support_agent_id,
                assigned_by_role=UserRole.SUPPORT_AGENT,
            )

    @pytest.mark.asyncio
    async def test_assign_to_ticket_not_found(self, ticket_service):
        """
        Тикет не найден
        """

        with pytest.raises(NotFoundError):
            await ticket_service.assign_to(
                ticket_id=uuid4(),
                assignee_id=uuid4(),
                assigned_by=uuid4(),
                assigned_by_role=UserRole.SUPPORT_AGENT,
            )

    @pytest.mark.asyncio
    async def test_assign_to_in_project_permission_check(
        self,
            ticket_service,
            mock_ticket_repo,
            ticket_in_progress,
            sample_project,
            sample_support,
            support_agent_id,
    ):
        """
        Если тикет в проекте — должна вызываться проверка прав
        """

        ticket_in_progress.project_id = sample_project.id
        await mock_ticket_repo.create(ticket_in_progress)

        response = await ticket_service.assign_to(
            ticket_id=ticket_in_progress.id,
            assignee_id=sample_support.id,
            assigned_by=support_agent_id,
            assigned_by_role=UserRole.SUPPORT_AGENT,
        )

        assert response.id == ticket_in_progress.id

    @pytest.mark.asyncio
    async def test_assign_to_in_project_no_permission(
            self,
            ticket_service,
            mock_ticket_repo,
            ticket_in_open,
            sample_project,
            sample_support,
    ):
        """
        Нет прав в проекте для назначения исполнителя
        """

        ticket_in_open.project_id = sample_project.id
        await mock_ticket_repo.create(ticket_in_open)

        with pytest.raises(PermissionDeniedError):
            await ticket_service.assign_to(
                ticket_id=ticket_in_open.id,
                assignee_id=sample_support.id,
                assigned_by=uuid4(),
                assigned_by_role=UserRole.SUPPORT_AGENT,
            )

    @pytest.mark.asyncio
    async def test_customer_cannot_assign_ticket(
        self, ticket_service, mock_ticket_repo, ticket_in_open, sample_support
    ):
        """
        Клиент не может назначать тикеты
        """

        await mock_ticket_repo.create(ticket_in_open)

        with pytest.raises(PermissionDeniedError):
            await ticket_service.assign_to(
                ticket_id=ticket_in_open.id,
                assignee_id=sample_support.id,
                assigned_by=uuid4(),
                assigned_by_role=UserRole.CUSTOMER,
            )

    @pytest.mark.asyncio
    async def test_assign_to_invalid_status(self, ticket_service, sample_ticket, sample_support):
        """
        Нельзя назначать тикет в недопустимом статусе
        """

        with pytest.raises(PermissionDeniedError):
            await ticket_service.assign_to(
                ticket_id=sample_ticket.id,
                assignee_id=sample_support.id,
                assigned_by=uuid4(),
                assigned_by_role=UserRole.SUPPORT_AGENT,
            )


class TestEdit:
    """
    Тесты для редактирования тикета
    """

    @pytest.mark.asyncio
    async def test_edit_success(
            self,
            mock_session,
            ticket_service,
            sample_ticket,
            reporter_id,
            mock_ticket_repo,
    ):
        """
        Успешное изменение тикета
        """

        new_tags = [Tag(name="bug", color="#0345fc"), Tag(name="feature", color="#fc0303")]
        data = TicketEdit(
            title="New title",
            description="New description",
            priority=TicketPriority.LOW,
            tags=new_tags,
        )
        response = await ticket_service.edit(sample_ticket.id, data, edited_by=reporter_id)

        mock_session.commit.assert_awaited_once()

        assert response.id == sample_ticket.id
        assert response.title == "New title"
        assert response.description == "New description"
        assert response.priority == TicketPriority.LOW
        assert response.tags == new_tags

        edited_ticket = await mock_ticket_repo.read(sample_ticket.id)

        assert edited_ticket is not None
        assert edited_ticket.title == "New title"
        assert edited_ticket.description == "New description"
        assert edited_ticket.priority == TicketPriority.LOW

    @pytest.mark.asyncio
    async def test_edit_not_found(self, ticket_service, reporter_id):
        """
        Тикет не найден
        """

        ticket_id = uuid4()
        data = TicketEdit(title="New title", description="New description")
        with pytest.raises(NotFoundError, match=f"Ticket with ID {ticket_id} not found"):
            await ticket_service.edit(ticket_id, data, edited_by=reporter_id)

    @pytest.mark.asyncio
    async def test_edit_partial_fields(self, ticket_service, sample_ticket, reporter_id):
        """
        Частичное редактирование полей
        """

        data = TicketEdit(title="New title", priority=TicketPriority.CRITICAL)
        response = await ticket_service.edit(sample_ticket.id, data, edited_by=reporter_id)

        assert response.id == sample_ticket.id
        assert response.title == "New title"
        assert response.priority == TicketPriority.CRITICAL
        assert response.description == sample_ticket.description


class TestArchive:
    """
    Тестирование архивирования тикета
    """

    @pytest.mark.asyncio
    async def test_archive_success(
            self, ticket_service, mock_ticket_repo, sample_ticket, reporter_id
    ):
        response = await ticket_service.archive(
            ticket_id=sample_ticket.id,
            archived_by=reporter_id,
            archived_by_role=UserRole.CUSTOMER,
        )

        assert response.id == sample_ticket.id
