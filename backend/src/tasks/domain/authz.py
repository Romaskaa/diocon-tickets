from uuid import UUID

from src.iam.domain.authz import AllOf, AnyOf, IsAdminRule, PermissionResult, Subject
from src.iam.domain.entities import User
from src.projects.domain.repos import ProjectMembershipRepository
from src.projects.domain.rules import IsProjectOwnerOrManagerRule, ProjectMembershipExistsRule

from .entities import Task
from .rules import (
    RequireProjectStaffRule,
    RequireStaffRule,
    TaskAssigneeStatusRule,
    TaskEditingRule,
    TaskReviewerStatusRule,
)
from .vo import TaskStatus


class TaskAuthZService:
    def __init__(self, project_membership_repo: ProjectMembershipRepository) -> None:
        self.project_membership_repo = project_membership_repo

    async def can_create_task(
            self, subject: Subject, project_id: UUID | None = None
    ) -> PermissionResult:
        rules = [RequireStaffRule(subject)]

        if project_id is not None:
            project_membership = await self.project_membership_repo.find(project_id, subject.id)
            rules.append(RequireProjectStaffRule(project_membership))

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_edit_task(self, subject: Subject, task: Task) -> PermissionResult:
        rules = [AnyOf(TaskEditingRule(subject, task), IsAdminRule(subject))]

        if task.project_id is not None:
            project_membership = await self.project_membership_repo.find(
                project_id=task.project_id, user_id=subject.id
            )
            rules.extend([
                AllOf(
                    ProjectMembershipExistsRule(project_membership),
                    IsProjectOwnerOrManagerRule(project_membership)
                )
            ])

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_change_status(
            self, subject: Subject, task: Task, new_status: TaskStatus
    ) -> PermissionResult:
        admin_policy = IsAdminRule(subject)

        project_membership = None
        if task.project_id is not None:
            project_membership = await self.project_membership_repo.find(
                project_id=task.project_id, user_id=subject.id
            )

        project_management_policy = AllOf(
            ProjectMembershipExistsRule(project_membership),
            IsProjectOwnerOrManagerRule(project_membership),
        )

        staff_policy = AllOf(
            RequireStaffRule(subject),
            AllOf(
                ProjectMembershipExistsRule(project_membership),
                RequireProjectStaffRule(project_membership),
            )
        )

        action_policy = AnyOf(
            TaskAssigneeStatusRule(subject, task, new_status),
            TaskReviewerStatusRule(subject, task, new_status),
        )
        staff_action_policy = AllOf(staff_policy, action_policy)

        auth_policy = AnyOf(admin_policy, project_management_policy, staff_action_policy)
        return auth_policy.check()

    async def can_assign_task(
            self, subject: Subject, task: Task, assignee: User
    ) -> PermissionResult:
        ...
