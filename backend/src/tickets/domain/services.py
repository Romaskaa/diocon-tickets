from uuid import UUID

from ...iam.domain.services import PermissionResult
from ...iam.domain.vo import UserRole
from .constants import NON_COMMENTABLE_STATUSES
from .entities import Ticket
from .vo import TicketStatus


def can_access_ticket(
        ticket: Ticket,
        user_id: UUID,
        user_role: UserRole,
        user_counterparty_id: UUID | None = None,
) -> PermissionResult:
    """Проверка есть ли у пользователя доступ к тикету"""

    # 1. Сотрудники поддержки имеют доступ ко всем тикетам
    if user_role.is_support():
        return PermissionResult(True)

    # 2. Ограничения для клиентов
    if user_role.is_customer():

        # 2.1 Обычный клиент видит только свои тикеты
        if user_role == UserRole.CUSTOMER:
            # Проверка на инициатора и соответствия контрагента
            if ticket.reporter_id == user_id and ticket.counterparty_id == user_counterparty_id:
                return PermissionResult(True)

            return PermissionResult(
                False, "Customer can access to tickets in which he is the reporter"
            )

        # 2.2 Админ контрагента видит все тикеты своего контрагента
        if user_role == UserRole.CUSTOMER_ADMIN:
            if ticket.counterparty_id == user_counterparty_id:
                return PermissionResult(True)

            return PermissionResult(
                False, "Customer admin can access to tickets of his counterparty"
            )

    return PermissionResult(False, "Access denied for this ticket")


def can_create_ticket(
        user_role: UserRole,
        user_counterparty_id: UUID | None = None,
        counterparty_id: UUID | None = None,
) -> PermissionResult:
    """Может ли пользователь создавать тикет"""

    # 1. Внутренние сотрудники могут создавать любые тикеты
    if user_role.is_internal():
        return PermissionResult(True)

    # 2. Клиенты могут создавать тикеты только в рамках своего контрагента
    if user_role.is_customer() and counterparty_id != user_counterparty_id:
        return PermissionResult(False, "Customers can only create tickets in their counterparty")

    return PermissionResult(True)


def can_assign_to(
        ticket: Ticket,
        assignee_id: UUID,
        assignee_role: UserRole,
        user_id: UUID,
        user_role: UserRole,
) -> PermissionResult:
    """Можно ли назначить тикет на пользователя"""

    # 1. Назначать тикет может только внутренний сотрудник
    if not user_role.is_support():
        return PermissionResult(False, "Only support team can assign ticket")

    # 2. Назначить тикет можно только на сотрудников поддержки
    if not assignee_role.is_support():
        return PermissionResult(False, "Tickets can only be assigned to support team")

    # 3. Переназначение тикета на самого себя
    if ticket.assignee_id is not None and assignee_id == user_id:

        # 3.1. Агент поддержки не может назначить себя на уже назначенный тикет
        if user_role == UserRole.SUPPORT_AGENT:
            return PermissionResult(
                False, "You cannot assign yourself to an already assigned ticket"
            )

        # 3.2. Менеджеры поддержки могут назначить самих себя исполнителями тикета
        if user_role in {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
            return PermissionResult(True)

    return PermissionResult(True)


def can_change_status(
        ticket: Ticket,
        new_status: TicketStatus,
        user_id: UUID,
        user_role: UserRole,
        user_counterparty_id: UUID | None = None,
) -> PermissionResult:
    """Может ли пользователь менять статус тикета"""

    # 1. Системный администратор и менеджер могут устанавливать все статусы
    if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
        return PermissionResult(True)

    # 2. Агент поддержки не может согласовывать тикеты
    if user_role == UserRole.SUPPORT_AGENT:
        if ticket.status == TicketStatus.PENDING_APPROVAL:
            return PermissionResult(False, "Support agent cannot approve ticket")

        if new_status in {
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            TicketStatus.WAITING,
            TicketStatus.RESOLVED,
            TicketStatus.CLOSED,
        }:
            return PermissionResult(True)

    # 3. Клиенты могут взаимодействовать с тикетами своего контрагента
    if user_role.is_customer() and ticket.counterparty_id == user_counterparty_id:

        if user_role == UserRole.CUSTOMER_ADMIN:
            # 3.1 Администратор со стороны клиента может согласовывать тикеты своего контрагента
            if ticket.status == TicketStatus.PENDING_APPROVAL and new_status in {
                TicketStatus.OPEN, TicketStatus.REJECTED
            }:
                return PermissionResult(True)

            # 3.2 Может переоткрывать любой тикет своего контрагента
            if new_status == TicketStatus.REOPENED:
                return PermissionResult(True)

        # 4. Обычный клиент может только переоткрывать свои закрытые тикеты
        if (
            user_role == UserRole.CUSTOMER and
            user_id in {ticket.created_by, ticket.reporter_id} and
            ticket.status == TicketStatus.CLOSED and
            new_status == TicketStatus.REOPENED
        ):
            return PermissionResult(True)

    return PermissionResult(
        False, f"Role '{user_role}' is not allowed to change status to '{new_status}'"
    )


def can_archive_ticket(ticket: Ticket, user_id: UUID, user_role: UserRole) -> PermissionResult:
    """Может ли пользователь архивировать тикет"""

    # 1. Является ли пользователь создателем или инициатором
    is_creator_or_reporter = user_id in {ticket.created_by, ticket.reporter_id}

    # 2. Является ли пользователь внутренним менеджером
    is_manager = user_role in {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}

    # 3. Архивировать тикет может только инициатор/создатель или менеджер поддержки
    if not (is_creator_or_reporter or is_manager):
        return PermissionResult(
            False, "Only the reporter/creator or support manager can archive ticket"
        )

    return PermissionResult(True)


def can_comment_ticket(
        ticket: Ticket,
        user_id: UUID,
        user_role: UserRole,
        user_counterparty_id: UUID | None = None,
) -> PermissionResult:
    """Может ли пользователь оставлять комментарии"""

    # 1. Проверка, что тикет в правильном статусе
    if ticket.status in NON_COMMENTABLE_STATUSES:
        return PermissionResult(False, f"You cannot comment ticket in status - {ticket.status}")

    # 2. Клиент может комментировать только свои тикеты
    if user_role == UserRole.CUSTOMER and ticket.reporter_id != user_id:
        return PermissionResult(False, "Customer can only comment his own tickets")

    # 3. Администратор клиента может комментировать все тикеты своего контрагента
    if user_role == UserRole.CUSTOMER_ADMIN and ticket.counterparty_id != user_counterparty_id:
        return PermissionResult(
            False, "Customer admin can only comment on tickets of his counterparty"
        )

    return PermissionResult(True)


def can_view_tickets(): ...
