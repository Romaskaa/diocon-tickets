import uuid

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError
from src.tickets.domain.constants import ALLOWED_TRANSITIONS
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import Priority, Tag, TicketNumber, TicketStatus, TicketType

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
def ticket_number():
    return TicketNumber(value="WEB-26-00000145")


@pytest.fixture
def ticket_in_new(reporter_id, support_agent_id, ticket_number):
    return Ticket.create(
        number=ticket_number,
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        priority=Priority.MEDIUM,
        counterparty_id=uuid.uuid4(),
    )


@pytest.fixture
def ticket_in_pending_approval(reporter_id, ticket_number):
    return Ticket.create(
        number=ticket_number,
        reporter_id=reporter_id,
        created_by=reporter_id,
        created_by_role=UserRole.CUSTOMER,
        title="Тестовый тикет от клиента",
        description="Описание",
        priority=Priority.HIGH,
        counterparty_id=uuid.uuid4(),
    )


@pytest.fixture
def ticket_in_open(reporter_id, support_agent_id, ticket_number):
    ticket = Ticket.create(
        number=ticket_number,
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        priority=Priority.MEDIUM,
        counterparty_id=uuid.uuid4(),
    )
    ticket.status = TicketStatus.OPEN
    return ticket


@pytest.fixture
def ticket_in_progress(reporter_id, support_agent_id, ticket_number):
    ticket = Ticket.create(
        number=ticket_number,
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        priority=Priority.HIGH,
        counterparty_id=uuid.uuid4(),
    )
    ticket.status = TicketStatus.IN_PROGRESS
    return ticket


# ====================== Тест кейсы ======================


def test_empty_title_raises_error(reporter_id, created_by_id, ticket_number):
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Ticket.create(
            number=ticket_number,
            reporter_id=reporter_id,
            created_by=created_by_id,
            created_by_role=UserRole.SUPPORT_AGENT,
            title="   ",
        )


class TestCreate:
    """
    Тесты для создания тикета
    """

    def test_create_ticket_minimal_success(self, reporter_id, created_by_id, ticket_number):
        ticket = Ticket.create(
            number=ticket_number,
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
        assert ticket.number == ticket_number
        assert len(ticket.history) == 1
        assert ticket.history[0].action == "ticket_created"

    def test_create_customer_ticket_requires_counterparty(
        self, reporter_id, created_by_id, ticket_number
    ):
        with pytest.raises(InvariantViolationError) as exc:
            Ticket.create(
                number=ticket_number,
                reporter_id=reporter_id,
                created_by=created_by_id,
                created_by_role=UserRole.CUSTOMER,
                title="Не работает оплата",
                counterparty_id=None,
            )

        assert "must be linked to a counterparty" in str(exc.value).lower()

    def test_create_ticket_with_project_and_counterparty(
        reporter_id, created_by_id, ticket_number, project_id, counterparty_id
    ):
        ticket = Ticket.create(
            number=ticket_number,
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

    @pytest.fixture
    def ticket_factory(self):
        """
        Фабрика для создания тикета с заданным статусом
        """

        def create(status: TicketStatus) -> Ticket:
            return Ticket(
                id=uuid.uuid4(),
                created_by=uuid.uuid4(),
                created_by_role=UserRole.SUPPORT_AGENT,
                reporter_id=uuid.uuid4(),
                number=TicketNumber("TEST-26-00000001"),
                title="Transition test",
                description="",
                type=TicketType.SERVICE_REQUEST,
                status=status,
                priority=Priority.MEDIUM,
                tags=[],
                attachments=[],
                history=[],
            )

        return create

    @pytest.mark.parametrize(
        ("from_status", "to_status"), [
            (source, destination)
            for source, targets in ALLOWED_TRANSITIONS.items()
            for destination in targets
        ]
    )
    def test_valid_transitions(self, ticket_factory, from_status, to_status):
        """
        Тестирование успешных переходов в разрешённые статусы
        """

        ticket = ticket_factory(from_status)

        changed_by = uuid.uuid4()
        ticket.change_status(to_status, changed_by=changed_by)

        assert ticket.status == to_status
        assert len(ticket.history) == 1

        entry = ticket.history[0]

        assert entry.action == "status_changed"
        assert entry.old_value == from_status
        assert entry.new_value == to_status.value
        assert entry.actor_id == changed_by

        # При закрытии тикета должно устанавливаться поле `closed_at`
        if to_status == TicketStatus.CLOSED:
            assert ticket.closed_at is not None
        else:
            assert ticket.closed_at is None

    @pytest.mark.parametrize(
        ("from_status", "to_status"), [
            (source, destination)
            for source in list(TicketStatus)
            for destination in list(TicketStatus)
            if destination not in ALLOWED_TRANSITIONS.get(source, [])
        ]
    )
    def test_invalid_transition_must_raises_error(self, ticket_factory, from_status, to_status):
        """
        При невалидном переходе должна выбрасываться ошибка
        """

        ticket = ticket_factory(from_status)
        original_status = ticket.status

        with pytest.raises(InvalidStateError, match="Not allowed status transition"):
            ticket.change_status(to_status, changed_by=uuid.uuid4())

        assert ticket.status == original_status
        assert len(ticket.history) == 0
        assert ticket.closed_at is None


class TestAssignTo:
    """
    Тестирование назначения тикета на исполнителя
    """

    def test_assign_free_ticket_success(self, ticket_in_open, support_agent_id):
        """
        Успешное назначение исполнителя на свободный тикет
        """

        assignee_id = uuid.uuid4()
        ticket_in_open.assign(assignee_id=assignee_id, assigned_by=support_agent_id)

        assert ticket_in_open.assignee_id == assignee_id
        assert ticket_in_open.history[-1].action == "assigned"
        assert ticket_in_open.updated_at > ticket_in_open.created_at

    def test_reassign_ticket_success(self, ticket_in_open, support_agent_id):
        """
        Успешное переназначение исполнителя тикета
        """

        first_support_agent_id = uuid.uuid4()
        ticket_in_open.assign(assignee_id=first_support_agent_id, assigned_by=support_agent_id)
        old_updated_at = ticket_in_open.updated_at

        second_agent_id = uuid.uuid4()
        ticket_in_open.assign(assignee_id=second_agent_id, assigned_by=first_support_agent_id)

        assert ticket_in_open.assignee_id == second_agent_id
        assert ticket_in_open.history[-1].action == "assigned"
        assert ticket_in_open.updated_at > old_updated_at

    def test_assign_same_user_do_nothing(self, ticket_in_open, support_agent_id):
        """
        При назначении того же пользователя не изменяется состояние тикета
        """

        assignee_id = uuid.uuid4()
        ticket_in_open.assign(assignee_id=assignee_id, assigned_by=support_agent_id)
        old_updated_at = ticket_in_open.updated_at
        old_ticket_history_length = len(ticket_in_open.history)

        ticket_in_open.assign(assignee_id=assignee_id, assigned_by=support_agent_id)

        assert len(ticket_in_open.history) == old_ticket_history_length
        assert ticket_in_open.assignee_id == assignee_id
        assert old_updated_at == ticket_in_open.updated_at

    @pytest.mark.parametrize(
        "new_status", [
            TicketStatus.NEW,
            TicketStatus.PENDING_APPROVAL,
            TicketStatus.CLOSED,
            TicketStatus.REOPENED,
        ]
    )
    def test_cannot_assign_when_status_not_allowed(self, ticket_in_open, new_status):
        """
        Нельзя назначить исполнителя при невалидном статусе
        """

        ticket_in_open.status = new_status

        with pytest.raises(InvalidStateError, match="Cannot assign ticket in status"):
            ticket_in_open.assign(assignee_id=uuid.uuid4(), assigned_by=uuid.uuid4())

        assert ticket_in_open.assignee_id is None


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
            number=TicketNumber("WEB-26-00000005"),
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
            priority=Priority.HIGH,
            tags=new_tags,
        )

        assert ticket.title == "New title"
        assert ticket.description == "New description"
        assert ticket.priority == Priority.HIGH
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
            priority=Priority.MEDIUM,
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
        ticket.change_status(new_status=TicketStatus.OPEN, changed_by=reporter_id)

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
    def created_ticket(self):
        return Ticket.create(
            number=TicketNumber("WEB-26-00000005"),
            reporter_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            created_by_role=UserRole.CUSTOMER,
            title="Initial ticket",
            description="Initial description",
            tags=[Tag(name="bug"), Tag(name="feature")],
            counterparty_id=uuid.uuid4(),
        )

    def test_archive_by_creator_success(self, created_ticket):
        """
        Успешная архивация активного тикета
        """

        created_ticket.archive(archived_by=uuid.uuid4())

        excepted_history_length = 2

        assert created_ticket.is_deleted is True
        assert len(created_ticket.history) == excepted_history_length
        assert created_ticket.history[-1].action == "ticket_archived"

    def test_archive_already_archived_do_nothing(self, created_ticket):
        """
        При архивации уже заархивированного тикета не должно меняться состояние
        """

        created_ticket.archive(archived_by=uuid.uuid4())
        old_updated_at = created_ticket.updated_at

        # Повторная архивация
        created_ticket.archive(archived_by=uuid.uuid4())

        excepted_history_length = 2

        assert created_ticket.is_deleted is True
        assert len(created_ticket.history) == excepted_history_length
        assert old_updated_at == created_ticket.updated_at
