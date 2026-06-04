from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.tickets.domain.services import can_access_ticket, can_comment_ticket
from src.tickets.domain.vo import TicketStatus


def make_mock_ticket(status: TicketStatus, reporter_id: UUID, counterparty_id: UUID):
    """
    Создание минимального мок объекта тикета с необходимыми аттрибутами
    """

    ticket = MagicMock()
    ticket.id = uuid4()
    ticket.status = status
    ticket.reporter_id = reporter_id
    ticket.counterparty_id = counterparty_id
    return ticket


class TestCanAccessTicket:
    """
    Тесты для проверки доступа к тикету
    """

    @pytest.mark.parametrize(
        "user_role", [UserRole.ADMIN, UserRole.SUPPORT_MANAGER, UserRole.SUPPORT_AGENT]
    )
    def test_support_staff_have_full_access(self, user_role):
        """
        Сотрудники поддержки имеют полный доступ к тикету
        """

        ticket = make_mock_ticket(
            status=TicketStatus.NEW, reporter_id=uuid4(), counterparty_id=uuid4()
        )
        permission = can_access_ticket(ticket, user_id=uuid4(), user_role=user_role)

        assert permission.allowed is True

    def test_customer_has_access_as_reporter(self):
        """
        Клиент имеет доступ, когда он инициатор
        """

        user_id = uuid4()
        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=TicketStatus.NEW, reporter_id=user_id, counterparty_id=counterparty_id
        )

        permission = can_access_ticket(
            ticket=ticket,
            user_id=user_id,
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=counterparty_id
        )

        assert permission.allowed is True

    def test_customer_access_wrong_ticket(self):
        """
        Попытка клиента получить доступ к тикету другого контрагента
        """

        ticket = make_mock_ticket(
            status=TicketStatus.NEW, reporter_id=uuid4(), counterparty_id=uuid4()
        )
        permission = can_access_ticket(
            ticket=ticket,
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=uuid4(),
        )

        assert permission.allowed is False
        assert "reporter" in permission.reason

    def test_customer_admin_access_same_counterparty(self):
        """
        Администратор клиента имеет доступ ко всем тикетам своего контрагента
        """

        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=TicketStatus.OPEN,
            reporter_id=uuid4(),
            counterparty_id=counterparty_id,
        )

        permission = can_access_ticket(
            ticket=ticket,
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER_ADMIN,
            user_counterparty_id=counterparty_id,
        )

        assert permission.allowed is True

    def test_customer_admin_access_wrong_counterparty(self):
        """
        Попытка администратора клиента обратиться к тикету другого контрагента,
        должна быть неудачной.
        """

        ticket = make_mock_ticket(
            status=TicketStatus.IN_PROGRESS, reporter_id=uuid4(), counterparty_id=uuid4()
        )

        permission = can_access_ticket(
            ticket=ticket,
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER_ADMIN,
            user_counterparty_id=uuid4(),
        )

        assert permission.allowed is False
        assert "counterparty" in permission.reason


class TestCanCommentTicket:
    """
    Тесты для проверки прав на комментирование тикета
    """

    @pytest.mark.parametrize(
        "ticket_status", [TicketStatus.CLOSED, TicketStatus.REJECTED, TicketStatus.CANCELED]
    )
    def test_forbidden_on_final_statuses(self, ticket_status):
        """
        Комментирование тикета запрещено на финальных статусах
        """

        user_id = uuid4()
        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=ticket_status, reporter_id=user_id, counterparty_id=counterparty_id
        )

        permission = can_comment_ticket(
            ticket,
            user_id=user_id,
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=counterparty_id,
        )

        assert permission.allowed is False
        assert "cannot comment ticket in status" in permission.reason

    @pytest.mark.parametrize(
        "ticket_status",
        [
            TicketStatus.NEW,
            TicketStatus.PENDING_APPROVAL,
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            TicketStatus.WAITING,
            TicketStatus.REOPENED,
        ],
    )
    def test_allowed_on_active_statuses_for_customer_owner(self, ticket_status):
        """
        Клиент-автор может комментировать активные тикеты
        """

        user_id = uuid4()
        counterparty_id = uuid4()
        ticket = make_mock_ticket(ticket_status, user_id, counterparty_id)

        permission = can_comment_ticket(
            ticket,
            user_id=user_id,
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=counterparty_id,
        )

        assert permission.allowed is True

    def test_customer_cannot_comment_others_tickets(self):
        """
        Клиент может комментировать только тикеты своего контрагента
        """

        ticket = make_mock_ticket(
            status=TicketStatus.IN_PROGRESS, reporter_id=uuid4(), counterparty_id=uuid4()
        )

        permission = can_comment_ticket(
            ticket,
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=ticket.counterparty_id,
        )

        assert permission.allowed is False
        assert "his" in permission.reason.lower()

    def test_customer_admin_can_comment_own_counterparty(self):
        """
        Администратор клиента может комментировать тикеты своего контрагента
        """

        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=TicketStatus.WAITING, reporter_id=uuid4(), counterparty_id=counterparty_id
        )

        permission = can_comment_ticket(
            ticket=ticket,
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER_ADMIN,
            user_counterparty_id=counterparty_id,
        )

        assert permission.allowed is True

    def test_customer_admin_cannot_comment_other_counterparty(self):
        """
        Администратор клиента не может комментировать тикеты другого контрагента
        """

        ticket = make_mock_ticket(
            status=TicketStatus.OPEN, reporter_id=uuid4(), counterparty_id=uuid4()
        )

        permission = can_comment_ticket(
            ticket=ticket,
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER_ADMIN,
            user_counterparty_id=uuid4(),
        )

        assert permission.allowed is False

    @pytest.mark.parametrize(
        "user_role", [UserRole.ADMIN, UserRole.SUPPORT_MANAGER, UserRole.SUPPORT_AGENT]
    )
    def test_internal_roles_can_comment_active_tickets(self, user_role):
        """
        Внутренние сотрудники могут комментировать любые активные тикеты
        """

        ticket = make_mock_ticket(
            status=TicketStatus.IN_PROGRESS, reporter_id=uuid4(), counterparty_id=uuid4()
        )

        permission = can_comment_ticket(ticket, user_id=uuid4(), user_role=user_role)

        assert permission.allowed is True
