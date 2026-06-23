from typing import ClassVar

from src.iam.domain.authz import PermissionResult, Subject
from src.iam.domain.vo import UserRole
from src.projects.domain.entities import ProjectMembership
from src.projects.domain.vo import ProjectRole

from .entities import Task
from .vo import TaskStatus


class RequireStaffRule:
    ALLOWED_USER_ROLES: ClassVar[set[UserRole]] = {
        UserRole.ADMIN,
        UserRole.SUPPORT_MANAGER,
        UserRole.SUPPORT_AGENT,
        UserRole.DEVELOPER,
        UserRole.FINANCE,
        UserRole.ACCOUNT_MANAGER,
    }

    def __init__(self, subject: Subject) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        for user_role in self.ALLOWED_USER_ROLES:
            if self.subject.has_role(user_role):
                return PermissionResult(True)

        return PermissionResult(False, "Only staff can create tasks")


class RequireProjectStaffRule:
    ALLOWED_PROJECT_ROLES: ClassVar[set[ProjectRole]] = {
        ProjectRole.CONTRIBUTOR, ProjectRole.MANAGER, ProjectRole.OWNER
    }

    def __init__(self, membership: ProjectMembership | None = None) -> None:
        self.membership = membership

    def check(self) -> PermissionResult:
        if self.membership is None:
            return PermissionResult(False, "You are not member of this project")

        for allowed_project_role in self.ALLOWED_PROJECT_ROLES:
            if self.membership.has_role(allowed_project_role):
                return PermissionResult(True)

        return PermissionResult(
            False,
            "Project role must be one of: "
            f"{', '.join(r.value for r in self.ALLOWED_PROJECT_ROLES)}",
        )


class TaskEditingRule:
    def __init__(self, subject: Subject, task: Task) -> None:
        self.subject = subject
        self.task = task

    def check(self) -> PermissionResult:
        if self.subject.id in {self.task.assignee_id, self.task.created_by}:
            return PermissionResult(True)

        return PermissionResult(False, "Only assignee or creator can edit this task")


class TaskReviewerStatusRule:
    """
    Правило перевода задачи в следующий статус для проверяющего.
    """

    ALLOWED_NEXT_STATUSES: ClassVar[set[TaskStatus]] = {
        TaskStatus.TO_FIX,
        TaskStatus.TO_TEST,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    }

    def __init__(self, subject: Subject, task: Task, new_status: TaskStatus) -> None:
        self.subject = subject
        self.task = task
        self.new_status = new_status

    def check(self) -> PermissionResult:
        if self.task.reviewer_id != self.subject.id:
            return PermissionResult(False, "You are not the reviewer for this task")

        if self.task.status != TaskStatus.TO_REVIEW:
            return PermissionResult(False, "Task is not in TO_REVIEW status")

        if self.new_status not in self.ALLOWED_NEXT_STATUSES:
            return PermissionResult(
                False,
                f"Task reviewer can only change to: "
                f"{', '.join([status.value() for status in self.ALLOWED_NEXT_STATUSES])}",
            )

        return PermissionResult(True)


class TaskAssigneeStatusRule:
    """
    Правило перевода задачи в новый статус для её исполнителя.
    """

    ALLOWED_NEXT_STATUSES: ClassVar[set[TaskStatus]] = {
        TaskStatus.BACKLOG,
        TaskStatus.TODO,
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.PAUSED,
        TaskStatus.TO_REVIEW,
        TaskStatus.TO_TEST,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    }

    def __init__(self, subject: Subject, task: Task, new_status: TaskStatus) -> None:
        self.subject = subject
        self.task = task
        self.new_status = new_status

    def check(self) -> PermissionResult:
        if self.task.assignee_id != self.subject.id:
            return PermissionResult(False, "You are not the assignee of this task")

        if self.new_status not in self.ALLOWED_NEXT_STATUSES:
            return PermissionResult(
                False,
                f"Task assignee can only change to: "
                f"{', '.join([status.value() for status in self.ALLOWED_NEXT_STATUSES])}",
            )

        return PermissionResult(True)
