from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.tickets.domain.services import (
    can_access_ticket,
    can_archive_ticket,
    can_assign_to,
    can_change_status,
    can_comment_ticket,
    can_create_ticket,
)
from src.tickets.domain.vo import TicketStatus


def make_mock_ticket(
    status: TicketStatus = TicketStatus.OPEN,
    reporter_id: UUID | None = None,
    counterparty_id: UUID | None = None,
    created_by: UUID | None = None,
    assignee_id: UUID | None = None,
) -> MagicMock:
    ticket = MagicMock()
    ticket.id = uuid4()
    ticket.status = status
    ticket.reporter_id = reporter_id or uuid4()
    ticket.counterparty_id = counterparty_id or uuid4()
    ticket.created_by = created_by or uuid4()
    ticket.assignee_id = assignee_id
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


class TestCanCreateTicket:

    @pytest.mark.parametrize(
        "user_role", [
            UserRole.ADMIN,
            UserRole.SUPPORT_MANAGER,
            UserRole.SUPPORT_AGENT,
            UserRole.DEVELOPER,
            UserRole.ACCOUNT_MANAGER,
            UserRole.FINANCE,
        ]
    )
    def test_any_internal_user_can_create_ticket(self, user_role):
        """
        Все внутренние сотрудники могут создавать тикет
        """

        permission = can_create_ticket(user_role=user_role)

        assert permission.allowed is True

    @pytest.mark.parametrize("user_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
    def test_customers_can_create_ticket_in_his_counterparty(self, user_role):
        """
        Клиента могут создавать тикеты только в рамках своего контрагента
        """

        counterparty_id = uuid4()
        permission = can_create_ticket(
            user_role=user_role,
            user_counterparty_id=counterparty_id,
            counterparty_id=counterparty_id,
        )

        assert permission.allowed is True

    @pytest.mark.parametrize("user_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
    def test_customers_cannot_create_ticket_in_other_counterparty(self, user_role):
        """
        Клиент не может создавать тикет в рамках другого контрагента
        """

        permission = can_create_ticket(
            user_role=user_role,
            user_counterparty_id=uuid4(),
            counterparty_id=uuid4(),
        )

        assert permission.allowed is False
        assert "counterparty" in permission.reason


class TestCanAssignTo:

    @pytest.mark.parametrize(
        "user_role", [UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN]
    )
    def test_any_supports_can_assign_free_ticket_to_other_agent(self, user_role):
        """
        Агент поддержки может назначить свободный тикет на другого агента
        """

        ticket = make_mock_ticket(assignee_id=None)

        permission = can_assign_to(
            ticket=ticket,
            assignee_id=uuid4(),
            assignee_role=UserRole.SUPPORT_AGENT,
            user_id=uuid4(),
            user_role=user_role,
        )

        assert permission.allowed is True

    def test_support_can_reassign_ticket_to_another_agent(self):
        """
        Агент поддержки может переназначить занятый тикет на другого агента
        """

        ticket = make_mock_ticket(assignee_id=uuid4())

        permission = can_assign_to(
            ticket,
            assignee_id=uuid4(),
            assignee_role=UserRole.SUPPORT_AGENT,
            user_id=uuid4(),
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert permission.allowed is True

    @pytest.mark.parametrize("user_role", [UserRole.SUPPORT_MANAGER, UserRole.ADMIN])
    def test_support_manager_or_above_can_reassign_ticket_to_self(self, user_role):
        """
        Менеджер поддержки (или выше) может переназначить тикет на самого себя
        """

        assignee_id = uuid4()
        support_manager_id = uuid4()
        ticket = make_mock_ticket(assignee_id=assignee_id)

        permission = can_assign_to(
            ticket,
            assignee_id=support_manager_id,
            assignee_role=user_role,
            user_id=support_manager_id,
            user_role=user_role,
        )

        assert permission.allowed is True

    @pytest.mark.parametrize(
        "user_role", [
            UserRole.CUSTOMER,
            UserRole.CUSTOMER_ADMIN,
            UserRole.DEVELOPER,
            UserRole.ACCOUNT_MANAGER,
            UserRole.FINANCE,
        ]
    )
    def test_non_support_cannot_assign(self, user_role):
        """
        Только сотрудники поддержки могут назначать тикеты
        """

        ticket = make_mock_ticket()
        permission = can_assign_to(
            ticket,
            assignee_id=uuid4(),
            assignee_role=UserRole.SUPPORT_AGENT,
            user_id=uuid4(),
            user_role=user_role,
        )

        assert permission.allowed is False
        assert "Only support team" in permission.reason

    @pytest.mark.parametrize(
        "assignee_role",
        [
            UserRole.CUSTOMER,
            UserRole.CUSTOMER_ADMIN,
            UserRole.DEVELOPER,
            UserRole.ACCOUNT_MANAGER,
            UserRole.FINANCE,
        ],
    )
    def test_cannot_assign_to_non_support_staff(self, assignee_role):
        """
        Нельзя назначить тикет на пользователя не являющимся сотрудником поддержки
        """

        ticket = make_mock_ticket()
        permission = can_assign_to(
            ticket,
            assignee_id=uuid4(),
            assignee_role=assignee_role,
            user_id=uuid4(),
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert permission.allowed is False
        assert "tickets can only be assigned to support team" in permission.reason.lower()

    def test_support_agent_cannot_self_assign_on_already_assigned(self):
        """
        Агент поддержки не может назначить себя на уже назначенный тикет
        """

        assignee_id = uuid4()
        support_agent_id = uuid4()
        ticket = make_mock_ticket(assignee_id=assignee_id)

        permission = can_assign_to(
            ticket,
            assignee_id=support_agent_id,
            assignee_role=UserRole.SUPPORT_AGENT,
            user_id=support_agent_id,
            user_role=UserRole.SUPPORT_AGENT,
        )
        assert not permission.allowed
        assert "cannot assign yourself" in permission.reason


class TestCanChangeStatus:

    @pytest.mark.parametrize("user_role", [UserRole.SUPPORT_MANAGER, UserRole.ADMIN])
    def test_admin_and_support_manager_can_change_any_status(self, user_role):
        """
        Админ и менеджер поддержки могут менять любой статус
        """

        ticket = make_mock_ticket(status=TicketStatus.OPEN)
        permission = can_change_status(
            ticket,
            new_status=TicketStatus.IN_PROGRESS,
            user_id=uuid4(),
            user_role=user_role,
        )

        assert permission.allowed is True

    def test_support_agent_cannot_approve(self):
        """
        Агент поддержки не может согласовывать тикет
        """

        ticket = make_mock_ticket(status=TicketStatus.PENDING_APPROVAL)
        permission = can_change_status(
            ticket,
            new_status=TicketStatus.OPEN,
            user_id=uuid4(),
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert not permission.allowed
        assert "cannot approve" in permission.reason.lower()

    @pytest.mark.parametrize(
        "new_status",
        [
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            TicketStatus.WAITING,
            TicketStatus.RESOLVED,
            TicketStatus.CLOSED,
        ],
    )
    def test_support_agent_can_move_to_workflow_statuses(self, new_status):
        """
        Агент может переводить тикет в рабочие статусы
        """

        ticket = make_mock_ticket(status=TicketStatus.OPEN)
        permission = can_change_status(
            ticket,
            new_status=new_status,
            user_id=uuid4(),
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert permission.allowed is True

    def test_agent_cannot_move_to_restricted_statuses(self):
        """
        Агент поддержки не может переоткрывать тикет
        """

        ticket = make_mock_ticket(status=TicketStatus.CLOSED)
        permission = can_change_status(
            ticket,
            new_status=TicketStatus.REOPENED,
            user_id=uuid4(),
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert not permission.allowed

    @pytest.mark.parametrize("new_status", [TicketStatus.OPEN, TicketStatus.REJECTED])
    def test_customer_admin_can_approve_or_reject(self, new_status):
        """
        Администратор со стороны клиента может согласовывать и отклонять тикеты
        """

        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=TicketStatus.PENDING_APPROVAL,
            counterparty_id=counterparty_id,
        )

        permission = can_change_status(
            ticket,
            new_status=new_status,
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER_ADMIN,
            user_counterparty_id=counterparty_id,
        )

        assert permission.allowed is True

    @pytest.mark.parametrize("user_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
    def test_customer_wrong_counterparty_denied(self, user_role):
        """
        Клиенты не могут менять статус у тикетов другого контрагента
        """

        ticket = make_mock_ticket(
            status=TicketStatus.PENDING_APPROVAL,
            counterparty_id=uuid4(),
        )
        permission = can_change_status(
            ticket,
            new_status=TicketStatus.OPEN,
            user_id=uuid4(),
            user_role=user_role,
            user_counterparty_id=uuid4(),
        )

        assert permission.allowed is False

    def test_customer_can_reopen_own_closed_ticket(self):
        """
        Клиент может переоткрывать свои закрытые тикеты
        """

        user_id = uuid4()
        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=TicketStatus.CLOSED,
            reporter_id=user_id,
            created_by=user_id,
            counterparty_id=counterparty_id,
        )

        permission = can_change_status(
            ticket,
            new_status=TicketStatus.REOPENED,
            user_id=user_id,
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=counterparty_id,
        )

        assert permission.allowed is True

    def test_customer_cannot_reopen_if_not_creator_or_reporter(self):
        """
        Клиент не может переоткрыть чужой тикет
        """

        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=TicketStatus.CLOSED,
            reporter_id=uuid4(),
            created_by=uuid4(),
            counterparty_id=counterparty_id,
        )

        permission = can_change_status(
            ticket,
            new_status=TicketStatus.REOPENED,
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=counterparty_id,
        )
        assert not permission.allowed

    def test_customer_cannot_reopen_if_not_closed(self):
        """
        Клиент не может переоткрыть ещё не закрытый тикет
        """

        user_id = uuid4()
        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=TicketStatus.REJECTED,
            reporter_id=user_id,
            created_by=user_id,
            counterparty_id=counterparty_id,
        )

        permission = can_change_status(
            ticket,
            new_status=TicketStatus.REOPENED,
            user_id=user_id,
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=counterparty_id,
        )
        assert not permission.allowed

    def test_customer_can_only_reopen(self):
        """
        Клиент может только переоткрывать тикеты
        """

        user_id = uuid4()
        counterparty_id = uuid4()
        ticket = make_mock_ticket(
            status=TicketStatus.OPEN,
            reporter_id=user_id,
            created_by=user_id,
            counterparty_id=counterparty_id,
        )

        permission = can_change_status(
            ticket,
            new_status=TicketStatus.IN_PROGRESS,
            user_id=user_id,
            user_role=UserRole.CUSTOMER,
            user_counterparty_id=counterparty_id,
        )

        assert not permission.allowed


class TestCanArchiveTicket:

    @pytest.mark.parametrize("user_role", [UserRole.ADMIN, UserRole.SUPPORT_MANAGER])
    def test_admin_or_support_manager_can_archive(self, user_role):
        """
        Админ и менеджер поддержки могут архивировать любые тикеты
        """

        ticket = make_mock_ticket()

        permission = can_archive_ticket(ticket, user_id=uuid4(), user_role=user_role)

        assert permission.allowed is True

    def test_creator_can_archive(self):
        """
        Создатель тикета может архивировать
        """

        creator_id = uuid4()
        ticket = make_mock_ticket(created_by=creator_id)
        permission = can_archive_ticket(ticket, user_id=creator_id, user_role=UserRole.CUSTOMER)
        assert permission.allowed is True

    def test_reporter_can_archive(self):
        """
        Инициатор тикета может архивировать
        """

        reporter_id = uuid4()
        ticket = make_mock_ticket(reporter_id=reporter_id)
        permission = can_archive_ticket(ticket, user_id=reporter_id, user_role=UserRole.CUSTOMER)
        assert permission.allowed is True

    def test_other_user_cannot_archive(self):
        """
        Посторонний пользователь не может архивировать
        """

        ticket = make_mock_ticket()
        permission = can_archive_ticket(ticket, user_id=uuid4(), user_role=UserRole.SUPPORT_AGENT)
        assert not permission.allowed
        assert "only the reporter/creator or support manager" in permission.reason.lower()


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
