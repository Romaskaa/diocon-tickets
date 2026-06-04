import uuid

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvariantViolationError
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import Tag, TicketNumber, TicketPriority, TicketStatus

# ====================== Fixtures ======================


@pytest.fixture
def ticket_id():
    return uuid.uuid4()


@pytest.fixture
def reporter_id():
    return uuid.uuid4()


@pytest.fixture
def customer_id():
    return uuid.uuid4()


@pytest.fixture
def support_agent_id():
    return uuid.uuid4()


@pytest.fixture
def customer_admin_id():
    return uuid.uuid4()


@pytest.fixture
def created_by_id():
    return uuid.uuid4()


@pytest.fixture
def project_id():
    return uuid.uuid4()


@pytest.fixture
def counterparty_id():
    return uuid.uuid4()


@pytest.fixture
def sample_ticket_number():
    return TicketNumber(value="WEB-26-00000145")


@pytest.fixture
def ticket_in_new(reporter_id, support_agent_id, sample_ticket_number):
    return Ticket.create(
        ticket_number=sample_ticket_number,
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        priority=TicketPriority.MEDIUM,
        counterparty_id=uuid.uuid4(),
    )


@pytest.fixture
def ticket_in_pending_approval(reporter_id, sample_ticket_number):
    return Ticket.create(
        ticket_number=sample_ticket_number,
        reporter_id=reporter_id,
        created_by=reporter_id,
        created_by_role=UserRole.CUSTOMER,
        title="Тестовый тикет от клиента",
        description="Описание",
        priority=TicketPriority.HIGH,
        counterparty_id=uuid.uuid4(),
    )


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
        counterparty_id=uuid.uuid4(),
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
        counterparty_id=uuid.uuid4(),
    )
    ticket.status = TicketStatus.IN_PROGRESS
    return ticket


# ====================== Тест кейсы ======================


def test_empty_title_raises_error(reporter_id, created_by_id, sample_ticket_number):
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=reporter_id,
            created_by=created_by_id,
            created_by_role=UserRole.SUPPORT_AGENT,
            title="   ",
        )


class TestCreate:
    """
    Тесты для создания тикета
    """

    def test_create_ticket_minimal_success(self, reporter_id, created_by_id, sample_ticket_number):
        ticket = Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=reporter_id,
            created_by=created_by_id,
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Проблема с авторизацией",
        )

        assert ticket.reporter_id == reporter_id
        assert ticket.created_by == created_by_id
        assert ticket.created_by_role == UserRole.SUPPORT_AGENT
        assert ticket.title == "Проблема с авторизацией"
        assert ticket.status == TicketStatus.NEW
        assert ticket.number == sample_ticket_number
        assert len(ticket.history) == 1
        assert ticket.history[0].action == "ticket_created"

    def test_create_customer_ticket_requires_counterparty(
        self, reporter_id, created_by_id, sample_ticket_number
    ):
        with pytest.raises(InvariantViolationError) as exc:
            Ticket.create(
                ticket_number=sample_ticket_number,
                reporter_id=reporter_id,
                created_by=created_by_id,
                created_by_role=UserRole.CUSTOMER,
                title="Не работает оплата",
                counterparty_id=None,
            )

        assert "must be linked to a counterparty" in str(exc.value).lower()

    def test_create_ticket_with_project_and_counterparty(
        reporter_id, created_by_id, sample_ticket_number, project_id, counterparty_id
    ):
        ticket = Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=reporter_id,
            created_by=created_by_id,
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Задача",
            project_id=project_id,
            counterparty_id=counterparty_id,
        )

        assert ticket.project_id == project_id
        assert ticket.counterparty_id == counterparty_id


class TestChangeStatus:
    """
    Тестирование изменение статуса тикета
    """

    def test_support_manager_can_do_any_transition(self, ticket_in_new):
        ticket = ticket_in_new

        allowed_transitions = [
            (TicketStatus.NEW, TicketStatus.PENDING_APPROVAL),
            (TicketStatus.NEW, TicketStatus.OPEN),
            (TicketStatus.PENDING_APPROVAL, TicketStatus.OPEN),
            (TicketStatus.OPEN, TicketStatus.IN_PROGRESS),
            (TicketStatus.IN_PROGRESS, TicketStatus.WAITING),
            (TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED),
            (TicketStatus.RESOLVED, TicketStatus.CLOSED),
            (TicketStatus.CLOSED, TicketStatus.REOPENED),
        ]

        for from_status, to_status in allowed_transitions:
            ticket.status = from_status

            ticket.change_status(
                new_status=to_status,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.SUPPORT_MANAGER,
            )
            assert ticket.status == to_status

    def test_customer_admin_can_approve_or_reject(self, ticket_in_pending_approval):
        ticket = ticket_in_pending_approval

        ticket.change_status(
            new_status=TicketStatus.OPEN,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.CUSTOMER_ADMIN,
        )
        assert ticket.status == TicketStatus.OPEN

    def test_customer_admin_cannot_move_to_in_progress(self, ticket_in_pending_approval):
        ticket = ticket_in_pending_approval

        with pytest.raises(PermissionDeniedError):
            ticket.change_status(
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.CUSTOMER_ADMIN,
            )

    def test_support_agent_cannot_approve(self, ticket_in_pending_approval):
        ticket = ticket_in_pending_approval

        with pytest.raises(PermissionDeniedError):
            ticket.change_status(
                new_status=TicketStatus.OPEN,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.SUPPORT_AGENT,
            )

    def test_invalid_transition_raises_error(self, ticket_in_new):
        ticket = ticket_in_new

        with pytest.raises(PermissionDeniedError, match="Not allowed status transition"):
            ticket.change_status(
                new_status=TicketStatus.RESOLVED,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.SUPPORT_AGENT,
            )

    def test_close_ticket_sets_closed_at(self, ticket_in_new):
        ticket = ticket_in_new
        ticket.status = TicketStatus.RESOLVED

        ticket.change_status(
            new_status=TicketStatus.CLOSED,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.SUPPORT_MANAGER,
        )

        assert ticket.status == TicketStatus.CLOSED
        assert ticket.closed_at is not None

    def test_customer_can_only_reopen_closed_ticket(self, ticket_in_new):
        ticket = ticket_in_new
        ticket.status = TicketStatus.CLOSED

        ticket.change_status(
            new_status=TicketStatus.REOPENED,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.CUSTOMER,
        )

        assert ticket.status == TicketStatus.REOPENED

        ticket.status = TicketStatus.CLOSED
        with pytest.raises(PermissionDeniedError):
            ticket.change_status(
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.CUSTOMER,
            )

    def test_support_manager_can_skip_pending_approval(self, ticket_in_new):
        ticket = ticket_in_new

        ticket.change_status(
            new_status=TicketStatus.OPEN,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.SUPPORT_MANAGER,
        )
        assert ticket.status == TicketStatus.OPEN

    def test_customer_admin_can_only_approve_from_pending(self, ticket_in_pending_approval):
        ticket = ticket_in_pending_approval

        ticket.change_status(
            new_status=TicketStatus.OPEN,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.CUSTOMER_ADMIN,
        )
        assert ticket.status == TicketStatus.OPEN

        with pytest.raises(PermissionDeniedError):
            ticket.change_status(
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.CUSTOMER_ADMIN,
            )


class TestAssignTo:
    """
    Тестирование назначения тикета на исполнителя
    """

    def test_support_agent_can_assign_ticket(self, ticket_in_open):
        ticket = ticket_in_open
        assignee_id = uuid.uuid4()
        excepted_history_length = 2

        ticket.assign_to(
            assignee_id=assignee_id,
            assignee_role=UserRole.SUPPORT_AGENT,
            assigned_by=uuid.uuid4(),
            assigned_by_role=UserRole.SUPPORT_AGENT,
        )

        assert ticket.assigned_to == assignee_id
        assert len(ticket.history) == excepted_history_length
        assert ticket.history[-1].action == "assigned"

    def test_support_manager_can_assign_ticket(self, ticket_in_open):
        ticket = ticket_in_open
        assignee_id = uuid.uuid4()

        ticket.assign_to(
            assignee_id=assignee_id,
            assignee_role=UserRole.SUPPORT_AGENT,
            assigned_by=uuid.uuid4(),
            assigned_by_role=UserRole.SUPPORT_MANAGER,
        )

        assert ticket.assigned_to == assignee_id

    def test_admin_can_assign_ticket(self, ticket_in_open):
        """
        Администратор может назначать тикеты
        """

        ticket = ticket_in_open
        assignee_id = uuid.uuid4()

        ticket.assign_to(
            assignee_id=assignee_id,
            assignee_role=UserRole.SUPPORT_AGENT,
            assigned_by=uuid.uuid4(),
            assigned_by_role=UserRole.ADMIN
        )

        assert ticket.assigned_to == assignee_id

    def test_customer_cannot_assign_ticket(self, ticket_in_open, customer_id):
        """
        Клиент не может назначать тикеты
        """

        ticket = ticket_in_open

        with pytest.raises(PermissionDeniedError, match="Only support team"):
            ticket.assign_to(
                assignee_id=uuid.uuid4(),
                assignee_role=UserRole.SUPPORT_AGENT,
                assigned_by=customer_id,
                assigned_by_role=UserRole.CUSTOMER,
            )

    def test_cannot_assign_in_invalid_status(self, ticket_in_open):
        """
        Нельзя назначать тикет в недопустимом статусе
        """

        ticket = ticket_in_open
        ticket.status = TicketStatus.CLOSED

        with pytest.raises(PermissionDeniedError, match="Cannot assign ticket in status"):
            ticket.assign_to(
                assignee_id=uuid.uuid4(),
                assignee_role=UserRole.SUPPORT_AGENT,
                assigned_by=uuid.uuid4(),
                assigned_by_role=UserRole.SUPPORT_AGENT,
            )

    def test_agent_can_assign_to_himself(self, ticket_in_open, support_agent_id):
        """
        Агент поддержки может назначить тикет на самого себя
        """

        ticket = ticket_in_open

        ticket.assign_to(
            assignee_id=support_agent_id,
            assignee_role=UserRole.SUPPORT_AGENT,
            assigned_by=support_agent_id,
            assigned_by_role=UserRole.SUPPORT_AGENT,
        )

        assert ticket.assigned_to == support_agent_id

    def test_can_reassign_to_another_agent(self, ticket_in_open):
        """
        Можно переназначить тикет на другого агента поддержки
        """

        ticket = ticket_in_open
        ticket.assign_to(
            assignee_id=uuid.uuid4(),
            assignee_role=UserRole.SUPPORT_AGENT,
            assigned_by=uuid.uuid4(),
            assigned_by_role=UserRole.SUPPORT_MANAGER,
        )
        excepted_history_length = 3

        new_assignee = uuid.uuid4()

        ticket.assign_to(
            assignee_id=new_assignee,
            assignee_role=UserRole.SUPPORT_MANAGER,
            assigned_by=uuid.uuid4(),
            assigned_by_role=UserRole.SUPPORT_AGENT,
        )

        assert ticket.assigned_to == new_assignee
        assert len(ticket.history) == excepted_history_length

    def test_assigning_to_same_person_does_nothing(self, ticket_in_open, support_agent_id):
        """
        Повторное назначение на того же человека не должно создавать новую запись в истории
        """

        ticket = ticket_in_open
        ticket.assigned_to = support_agent_id
        history_len_before = len(ticket.history)

        ticket.assign_to(
            assignee_id=support_agent_id,
            assignee_role=UserRole.ADMIN,
            assigned_by=uuid.uuid4(),
            assigned_by_role=UserRole.SUPPORT_AGENT,
        )

        assert len(ticket.history) == history_len_before

    def test_cannot_assigning_to_customer(self, ticket_in_open, customer_id):
        """
        Нельзя назначить тикет на клиента
        """

        with pytest.raises(PermissionDeniedError, match="can only be assigned to support team"):
            ticket_in_open.assign_to(
                assignee_id=customer_id,
                assignee_role=UserRole.CUSTOMER,
                assigned_by=uuid.uuid4(),
                assigned_by_role=UserRole.SUPPORT_AGENT,
            )


class TestEdit:
    """
    Тестирование редактирования тикета
    """

    @pytest.fixture
    def creator_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def reporter_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def ticket(self, reporter_id, creator_id):
        return Ticket.create(
            ticket_number=TicketNumber("WEB-26-00000005"),
            reporter_id=reporter_id,
            created_by=creator_id,
            created_by_role=UserRole.CUSTOMER,
            title="Initial ticket",
            description="Initial description",
            tags=[Tag(name="bug"), Tag(name="feature")],
            counterparty_id=uuid.uuid4(),
        )

    def test_edit_success(self, ticket, creator_id):
        """
        Успешное редактирование всех допустимых полей тикета
        """

        new_tags = [Tag(name="bug"), Tag(name="feature"), Tag(name="alert")]
        ticket.edit(
            edited_by=creator_id,
            title="New title",
            description="New description",
            priority=TicketPriority.HIGH,
            tags=new_tags,
        )

        assert ticket.title == "New title"
        assert ticket.description == "New description"
        assert ticket.priority == TicketPriority.HIGH
        assert ticket.tags == new_tags

        history_entry = ticket.history[-1]
        excepted_history_length = 5

        assert history_entry.actor_id == creator_id
        assert len(ticket.history) == excepted_history_length

    def test_edit_no_changes(self, ticket, reporter_id):
        """
        История изменений не меняется, если данные при редактировании не меняются
        """

        ticket.edit(
            edited_by=reporter_id,
            title="Initial ticket",
            description="Initial description",
            priority=TicketPriority.MEDIUM,
            tags=[Tag(name="bug"), Tag(name="feature")],
        )

        assert len(ticket.history) == 1

    def test_edit_forbidden_for_not_creator_or_reporter(self, ticket):
        """
        Нельзя редактировать тикет, если ты не автор или инициатор
        """

        with pytest.raises(PermissionDeniedError, match="Only author or reporter can edit ticket"):
            ticket.edit(edited_by=uuid.uuid4(), title="New title")

    def test_edit_in_not_allowed_status(self, ticket, reporter_id):
        """
        Нельзя редактировать тикет, который находится в неразрешённом статусе
        """

        # Изменение статуса на 'новый'
        ticket.change_status(
            new_status=TicketStatus.OPEN,
            changed_by=reporter_id,
            changed_by_role=UserRole.CUSTOMER_ADMIN,
        )

        with pytest.raises(
                InvariantViolationError, match="Cannot edit ticket in not allowed status"
        ):
            ticket.edit(edited_by=reporter_id, title="New title")

    def test_edit_empty_title_ignored(self, ticket, creator_id):
        """
        Нельзя устанавливать пустой заголовок и описание
        """

        ticket.edit(edited_by=creator_id, title="  ", description="  ")

        assert bool(ticket.title) is True
        assert len(ticket.history) == 1
        assert ticket.history[-1].action == "ticket_created"


class TestArchive:
    """
    Тесты для архивирования тикета
    """

    @pytest.fixture
    def creator_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def reporter_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def ticket(self, reporter_id, creator_id):
        return Ticket.create(
            ticket_number=TicketNumber("WEB-26-00000005"),
            reporter_id=reporter_id,
            created_by=creator_id,
            created_by_role=UserRole.CUSTOMER,
            title="Initial ticket",
            description="Initial description",
            tags=[Tag(name="bug"), Tag(name="feature")],
            counterparty_id=uuid.uuid4(),
        )

    def test_archive_by_creator_success(self, ticket, creator_id):
        """
        Успешная архивация тикета автором
        """

        ticket.archive(archived_by=creator_id, archived_by_role=UserRole.SUPPORT_AGENT)

        excepted_history_length = 2

        assert ticket.is_deleted is True
        assert ticket.updated_at > ticket.created_at
        assert len(ticket.history) == excepted_history_length
        assert ticket.history[-1].action == "ticket_archived"

    @pytest.mark.parametrize(
        "user_role", [
            UserRole.CUSTOMER,
            UserRole.CUSTOMER_ADMIN,
            UserRole.SUPPORT_AGENT,
            UserRole.SUPPORT_MANAGER,
            UserRole.ADMIN,
        ]
    )
    def test_archive_by_reporter_success(self, ticket, reporter_id, user_role):
        """
        Успешная архивация тикета инициатором
        """

        ticket.archive(archived_by=reporter_id, archived_by_role=user_role)

        assert ticket.is_deleted is True

    @pytest.mark.parametrize("user_role", [UserRole.ADMIN, UserRole.SUPPORT_MANAGER])
    def test_archive_by_required_staff_success(self, ticket, user_role):
        """
        Успешная архивация тикета определёнными сотрудниками
        """

        ticket.archive(archived_by=uuid.uuid4(), archived_by_role=user_role)

        assert ticket.is_deleted is True

    @pytest.mark.parametrize(
        "wrong_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN, UserRole.SUPPORT_AGENT]
    )
    def test_archive_forbidden_for_wrong_role_and_outsider_id(self, ticket, wrong_role):
        """
        Доступ запрещён если неверная роль и
        """

        with pytest.raises(
                PermissionDeniedError, match="Insufficient permissions to archive a ticket"
        ):
            ticket.archive(archived_by=uuid.uuid4(), archived_by_role=wrong_role)

    def test_archive_already_archived_does_nothing(self, ticket, reporter_id):
        """
        При архивации уже архивированного тикета, не должно обновляться состояние
        """

        ticket.archive(archived_by=reporter_id, archived_by_role=UserRole.SUPPORT_AGENT)

        deleted_at, updated_at = ticket.deleted_at, ticket.updated_at

        ticket.archive(archived_by=reporter_id, archived_by_role=UserRole.SUPPORT_MANAGER)

        assert ticket.is_deleted is True
        assert ticket.deleted_at == deleted_at
        assert ticket.updated_at == updated_at
