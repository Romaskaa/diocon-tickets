from uuid import UUID

from src.iam.domain.authz import AllOf, AnyOf, Not, PermissionResult, Subject
from src.iam.domain.entities import User
from src.iam.domain.rules import IsAdminRule, IsStaffRule

from .entities import Project, ProjectMember
from .repos import ProjectMemberRepository
from .rules import (
    GrantProjectRoleRule,
    IsProjectManagerRule,
    IsProjectOwnerOrManagerRule,
    IsProjectOwnerRule,
    IsMemberExistsRule,
    TargetRoleAssignmentRule,
)
from .vo import ProjectRole


class ProjectAuthZService:
    def __init__(self, member_repo: ProjectMemberRepository) -> None:
        self.member_repo = member_repo

    @staticmethod
    def can_create_project(subject: Subject) -> PermissionResult:
        return IsStaffRule(subject).check()

    async def can_archive_project(self, subject: Subject, project_id: UUID) -> PermissionResult:
        rules = [IsAdminRule(subject)]

        member = await self.member_repo.find(project_id, subject.id)
        rules.append(
            AllOf(
                IsMemberExistsRule(member),
                IsProjectOwnerRule(member),
            )
        )

        return AnyOf(*rules).check()

    async def can_manage_project(self, subject: Subject, project_id: UUID) -> PermissionResult:
        rules = [IsAdminRule(subject)]

        member = await self.member_repo.find(project_id, subject.id)
        rules.append(
            AllOf(
                IsMemberExistsRule(member),
                AnyOf(
                    IsProjectManagerRule(member),
                    IsProjectOwnerRule(member),
                )
            )
        )

        return AnyOf(*rules).check()

    async def can_add_member(
            self,
            subject: Subject,
            project: Project,
            invitee: User,
            target_roles: set[ProjectRole],
    ) -> PermissionResult:
        member = await self.member_repo.find(project.id, subject.id)
        actor_policy = AnyOf(
            IsAdminRule(subject),
            AllOf(
                IsMemberExistsRule(member),
                TargetRoleAssignmentRule(member, target_roles),
            )
        )
        invitee_policy = GrantProjectRoleRule(invitee, target_roles)
        return AllOf(actor_policy, invitee_policy).check()

    async def can_remove_member(
            self, subject: Subject, project_id: UUID, member_to_remove: ProjectMember
    ) -> PermissionResult:
        rules = [IsAdminRule(subject)]

        actor_member = await self.member_repo.find(project_id, subject.id)

        rules.append(
            AllOf(
                IsMemberExistsRule(actor_member),
                IsProjectOwnerOrManagerRule(actor_member),
                IsMemberExistsRule(member_to_remove),
                Not(IsProjectOwnerRule(member_to_remove)),
            )
        )

        return AnyOf(*rules).check()
    
    async def can_export_project(self, subject: Subject, project_id: UUID) -> PermissionResult:
        """
        Проверяет, может ли субъект экспортировать отчет по проекту.
        """

        member = await self.member_repo.find(project_id, subject.id)

        return AllOf(
            IsMemberExistsRule(member),
            AnyOf(
                IsProjectManagerRule(member),
                IsProjectOwnerRule(member),
            ),
        ).check()
