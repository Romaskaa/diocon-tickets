from uuid import UUID

from ...iam.domain.services import PermissionResult
from ...iam.domain.vo import UserRole
from .entities import Task
from .vo import TaskStatus


def can_create_task(user_role: UserRole) -> PermissionResult:
    # 1. Только определённые внутренние сотрудники могут создавать задачи
    if user_role not in {
        UserRole.DEVELOPER,
        UserRole.SUPPORT_AGENT,
        UserRole.SUPPORT_MANAGER,
        UserRole.ADMIN,
    }:
        return PermissionResult(
            False, "Task can only be created by: developer, support manager, admin"
        )

    return PermissionResult(True)


def can_edit_task(task: Task, user_id: UUID, user_role: UserRole) -> PermissionResult:
    """Может ли пользователь редактировать задачу"""

    # Разработчик может редактировать задачу, если он её создатель или текущий исполнитель
    if user_role in {
        UserRole.DEVELOPER,
        UserRole.SUPPORT_AGENT,
        UserRole.SUPPORT_MANAGER,
        UserRole.ADMIN,
    }:

        if user_id in {task.assignee_id, task.created_by}:
            return PermissionResult(True)

        return PermissionResult(
            False, "To edit a task you need to be assigned to it or the creator"
        )

    return PermissionResult(False, "You do not have permission to edit this task")


def can_move_status(
        task: Task, new_status: TaskStatus, user_id: UUID, user_role: UserRole
) -> PermissionResult:
    """Может ли пользователь переводить задачу в новый статус"""

    if user_role == UserRole.ADMIN:
        return PermissionResult(True)

    # Ответственный за задачу может одобрить или отклонить
    if task.reviewer_id == user_id:
        if task.status == TaskStatus.TO_REVIEW and new_status in {
            TaskStatus.IN_PROGRESS, TaskStatus.DONE
        }:
            return PermissionResult(True)

        return PermissionResult(False, "Task reviewer only can move to IN_PROGRESS or DONE status")

    # Специалист поддержки может переводить только свои задачи
    if user_role in {UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER}:
        if task.assignee_id != user_id:
            return PermissionResult(False, "You are not assigner for this task")

        # Исполнитель может переводить только в рабочие статусы
        if new_status in {
            TaskStatus.IN_PROGRESS,
            TaskStatus.BLOCKED,
            TaskStatus.TO_REVIEW,
            TaskStatus.DONE,
        }:
            return PermissionResult(True)

    return PermissionResult(
        False, f"User with role {user_role} cannot move this task to {new_status}"
    )


def can_assign_task(
        task: Task,
        assignee_role: UserRole,
        user_id: UUID,
        user_role: UserRole,
) -> PermissionResult:
    """Может ли пользователь назначать на задачу исполнителя"""

    # 1. Админ может назначать и переназначать задачи в любой момент времени
    if user_role == UserRole.ADMIN:
        return PermissionResult(True)

    # 2. Только поддержка и разработчики могут назначать задачи
    if user_role not in {UserRole.DEVELOPER, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER}:
        return PermissionResult(False, "Only developers or supports can assign tasks")

    # 3. Нельзя назначить задачу на клиента или другую неподходящую роль
    if assignee_role in {UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN, UserRole.FINANCE}:
        return PermissionResult(
            False, "Tasks can only be assigned to internal staff (developer, support)"
        )

    # 4. Если задача уже назначена, исполнитель может переназначить её
    if task.assignee_id is not None and task.assignee_id != user_id:
        return PermissionResult(False, "You can only reassign tasks assigned to yourself")

    return PermissionResult(True)


def can_request_review(
        task: Task, reviewer_role: UserRole, user_id: UUID, user_role: UserRole
) -> PermissionResult:
    """Может ли пользователь запросить ревью для задачи"""

    if user_role in {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
        return PermissionResult(True)

    # Запросить ревью можно только у разработчиков и сотрудников поддержки
    if reviewer_role in {
        UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN, UserRole.ACCOUNT_MANAGER, UserRole.FINANCE
    }:
        return PermissionResult(
            False, "You can request a review only from developers and support staff"
        )

    # Исполнитель может запросить ревью для своей задачи
    if task.assignee_id == user_id:
        return PermissionResult(True)

    return PermissionResult(False, "You don't have permission to request review for this task")


def can_review_task(task: Task, user_id: UUID, user_role: UserRole) -> PermissionResult:
    """Может ли пользователь проверить (одобрить/отклонить) задачу"""

    if task.reviewer_id != user_id and user_role not in {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
        return PermissionResult(False, "Only reviewer or manager can review task")

    return PermissionResult(True)


def can_archive_task(task: Task, user_id: UUID, user_role: UserRole) -> PermissionResult:
    """Может ли пользователь архивировать задачу"""

    # 1. Админ может переносить в архив любую задачу
    if user_role == UserRole.ADMIN:
        return PermissionResult(True)

    # 2. Архивировать может фактический создатель задачи
    if task.created_by == user_id:
        return PermissionResult(True)

    return PermissionResult(False, "Only the admin or creator can archive a task")


def can_view_tasks(user_role: UserRole) -> PermissionResult:
    """Может ли пользователь просматривать задачи"""

    # Просматривать задачи могут только внутренние сотрудники
    if not user_role.is_internal():
        return PermissionResult(False, "Only internal users can view tasks")

    return PermissionResult(True)
