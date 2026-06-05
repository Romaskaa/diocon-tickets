from uuid import UUID

from ...iam.domain.services import PermissionResult
from ...iam.domain.vo import UserRole
from ...tasks.domain.entities import Task
from ...tickets.domain.entities import Ticket
from .entities import Timesheet, Worklog


def can_log_time(
        ticket: Ticket | None,
        task: Task | None,
        user_id: UUID,
        user_role: UserRole,
) -> PermissionResult:
    """Может ли пользователь логгировать потраченное время"""

    if user_role == UserRole.ADMIN:
        return PermissionResult(True)

    # Только внутренние сотрудники могут логгировать время
    if user_role.is_customer():
        return PermissionResult(False, "Only internal staff can log time")

    # Логгировать время тикета может только его исполнитель
    if ticket is not None and ticket.assignee_id != user_id:
        return PermissionResult(False, "Only the ticket assignee can log the ticket time")

    # Логгировать время задачи может только её исполнитель
    if task is not None and task.assignee_id != user_id:
        return PermissionResult(False, "Only the task assignee can log the task time")

    return PermissionResult(True)


def can_edit_worklog(worklog: Worklog, user_id: UUID, user_role: UserRole) -> PermissionResult:
    """Может ли пользователь редактировать лог времени"""

    if user_role == UserRole.ADMIN:
        return PermissionResult(True)

    # Редактировать может только создатель записи
    if worklog.user_id != user_id:
        return PermissionResult(False, "Only author can edit worklog")

    return PermissionResult(True)


def can_create_timesheet(user_role: UserRole) -> PermissionResult:
    """Может ли пользователь сформировать ЛУРВ"""

    if not user_role.is_internal():
        return PermissionResult(False, "Only internal staff can create timesheet")

    return PermissionResult(True)


def can_submit_timesheet(
        timesheet: Timesheet, user_id: UUID, user_role: UserRole
) -> PermissionResult:
    """Может ли пользователь отправить на согласование ЛУРВ"""

    if user_role == UserRole.ADMIN:
        return PermissionResult(True)

    if timesheet.user_id != user_id:
        return PermissionResult(False, "Only author can submit timesheet")

    return PermissionResult(True)


def can_approve_timesheet(user_role: UserRole) -> PermissionResult:
    """Может ли пользователь согласовывать ЛУРВ"""

    if user_role in {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
        return PermissionResult(True)

    return PermissionResult(False, f"You - '{user_role}' cannot approve timesheet")
