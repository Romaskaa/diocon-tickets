from uuid import UUID

from ...iam.domain.services import PermissionResult
from ...iam.domain.vo import UserRole
from .entities import Task
from .vo import TaskStatus


def can_create_task() -> PermissionResult: ...


def can_move_task_status(
        task: Task, new_status: TaskStatus, user_id: UUID, user_role: UserRole
) -> PermissionResult:
    """Может ли пользователь переводить задачу в новый статус"""

    if user_role in {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
        return PermissionResult(True)

    # Специалист поддержки может переводить только свои задачи
    if user_role in {UserRole.SUPPORT_SPECIALIST, UserRole.SUPPORT_AGENT}:
        if task.assignee_id != user_id:
            return PermissionResult(False, "Support specialist can move only his tasks")

        # Исполнитель может переводить в рабочие статусы
        if new_status in {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.DONE}:
            return PermissionResult(True)

    return PermissionResult(
        False, f"User with role {user_role} cannot move this task to {new_status}"
    )


def can_assign_task() -> PermissionResult: ...
