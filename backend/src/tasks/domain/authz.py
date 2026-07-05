from uuid import UUID

from src.iam.domain.authz import AllOf, AnyOf, PermissionResult, Subject
from src.iam.domain.entities import User
from src.iam.domain.rules import IsAdminRule, IsStaffRule
from src.projects.domain.repos import ProjectMemberRepository
from src.projects.domain.rules import IsProjectOwnerOrManagerRule, IsMemberExistsRule

from .entities import Task
from .rules import (
    IsProjectStaffRule,
    IsTaskCreator,
    IsTaskReviewer,
    TaskAssigneeStatusRule,
    TaskEditingRule,
    TaskReviewerStatusRule,
)
from .vo import TaskStatus


class TaskAuthZService:
    def __init__(self, project_membership_repo: ProjectMemberRepository) -> None:
        self.project_membership_repo = project_membership_repo

    async def can_create_task(
            self, subject: Subject, project_id: UUID | None = None
    ) -> PermissionResult:
        rules = [IsStaffRule(subject)]

        if project_id is not None:
            project_membership = await self.project_membership_repo.find(project_id, subject.id)
            rules.append(IsProjectStaffRule(project_membership))

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_edit_task(self, subject: Subject, task: Task) -> PermissionResult:
        rules = [AnyOf(TaskEditingRule(subject, task), IsAdminRule(subject))]

        if task.project_id is not None:
            project_member = await self.project_membership_repo.find(task.project_id, subject.id)
            rules.extend([
                AllOf(
                    IsMemberExistsRule(project_member),
                    IsProjectOwnerOrManagerRule(project_member)
                )
            ])

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_change_status(
            self, subject: Subject, task: Task, new_status: TaskStatus
    ) -> PermissionResult:
        rules = [IsAdminRule(subject)]

        if task.project_id is not None:
            project_member = await self.project_membership_repo.find(task.project_id, subject.id)
            rules.append(
                AnyOf(
                    AllOf(
                        IsMemberExistsRule(project_member),
                        IsProjectOwnerOrManagerRule(project_member),
                    ),
                    AllOf(
                        IsMemberExistsRule(project_member),
                        IsProjectStaffRule(project_member),
                    ),
                )
            )

            auth_policy = AnyOf(*rules)
            return auth_policy.check()

        rules.extend((
            IsStaffRule(subject),
            AnyOf(
                TaskAssigneeStatusRule(subject, task, new_status),
                TaskReviewerStatusRule(subject, task, new_status)
            )
        ))

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_assign_task(
            self, subject: Subject, task: Task, assignee: User
    ) -> PermissionResult:
        rules = [IsAdminRule(subject), IsStaffRule(subject), IsStaffRule(assignee)]

        if task.project_id is not None:
            current_member = await self.project_membership_repo.find(task.project_id, subject.id)
            assignee_member = await self.project_membership_repo.find(task.project_id, assignee.id)

            member_rules = []
            for member in {current_member, assignee_member}:
                member_rules.extend((
                    IsMemberExistsRule(member),
                    IsProjectStaffRule(member),
                ))

            rules.append(AllOf(*member_rules))

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_request_review(
            self, subject: Subject, task: Task, reviewer: User
    ) -> PermissionResult:
        rules = [IsAdminRule(subject), IsStaffRule(subject)]

        if task.project_id is not None:
            current_member = await self.project_membership_repo.find(task.project_id, subject.id)
            reviewer_member = await self.project_membership_repo.find(task.project_id, reviewer.id)
            member_rules = []
            for member in {current_member, reviewer_member}:
                member_rules.extend((
                    IsMemberExistsRule(member),
                    IsProjectStaffRule(member),
                ))

            rules.append(AllOf(*member_rules))

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_review_task(self, subject: Subject, task: Task) -> PermissionResult:
        rules = [IsAdminRule(subject)]

        if task.project_id is not None:
            project_member = await self.project_membership_repo.find(task.project_id, subject.id)
            rules.append(
                AllOf(
                    IsMemberExistsRule(project_member),
                    IsProjectOwnerOrManagerRule(project_member),
                )
            )

        rules.append(IsTaskReviewer(subject, task))

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_archive_task(self, subject: Subject, task: Task) -> PermissionResult:
        rules = [IsAdminRule(subject)]

        if task.project_id is not None:
            project_member = await self.project_membership_repo.find(task.project_id, subject.id)
            rules.append(
                AllOf(
                    IsMemberExistsRule(project_member),
                    IsProjectOwnerOrManagerRule(project_member),
                )
            )

        rules.append(IsTaskCreator(subject, task))

        auth_policy = AnyOf(*rules)
        return auth_policy.check()

    async def can_view_task(
            self, subject: Subject, project_id: UUID | None = None
    ) -> PermissionResult:
        if project_id is not None:
            project_member = await self.project_membership_repo.find(project_id, subject.id)
            auth_policy = AllOf(
                IsMemberExistsRule(project_member),
                IsProjectStaffRule(project_member),
            )
            return auth_policy.check()

        auth_policy = IsStaffRule(subject)
        return auth_policy.check()
