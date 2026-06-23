"""
Реализация правил для авторизации.
"""

from typing import ClassVar

from dataclasses import dataclass

from src.iam.domain.authz import (
    AllOf,
    AnyOf,
    AuthorizationRule,
    BaseAuthContext,
    PermissionResult,
    Subject,
)
from src.iam.domain.entities import User
from src.iam.domain.vo import UserRole

from .entities import Project, ProjectMembership
from .vo import ProjectRole


@dataclass(frozen=True)
class ProjectContext(BaseAuthContext):
    project: Project
    current_membership: ProjectMembership | None = None


@dataclass(frozen=True, kw_only=True)
class AddMemberContext(ProjectContext):
    invitee: User
    target_role: ProjectRole


@dataclass(frozen=True, kw_only=True)
class RemoveMemberContext(ProjectContext):
    membership_to_remove: ProjectMembership


class HasAllowedCreationRoleRule(AuthorizationRule[BaseAuthContext]):
    ALLOWED_ROLES: ClassVar[set[ProjectRole]] = {role for role in UserRole if role.is_internal()}

    @classmethod
    def check(cls, ctx: BaseAuthContext) -> PermissionResult:
        for allowed_role in cls.ALLOWED_ROLES:
            if ctx.subject.has_role(allowed_role):
                return PermissionResult(True)

        return PermissionResult(False, "You don't have permission to create projects")


class IsUserPrincipalRule(AuthorizationRule[BaseAuthContext]):
    @staticmethod
    def check(ctx: BaseAuthContext) -> PermissionResult:
        if not ctx.subject.is_user:
            return PermissionResult(
                False, f"{ctx.subject.type.value.capitalize()}s cannot create projects"
            )

        return PermissionResult(True)


class ProjectMembershipExistsRule:
    """Пользователь должен быть участником проекта"""

    def __init__(self, membership: ProjectMembership) -> None:
        self.membership = membership

    def check(self) -> PermissionResult:
        if self.membership is None:
            return PermissionResult(False, "You are not member of the project")

        return PermissionResult(True)


class TargetRoleCompatibilityRule(AuthorizationRule[AddMemberContext]):
    """
    Проверка валидности назначенной проектной роли добавленному участнику.
    """

    def check(self, ctx: AddMemberContext) -> PermissionResult:
        if ctx.target_role == ProjectRole.OWNER:
            return PermissionResult(
                False, "OWNER role cannot be assigned through membership addition"
            )

        allowed_project_roles = self._get_allowed_project_roles_for_user(ctx.invitee.role)
        if ctx.target_role not in allowed_project_roles:
            return PermissionResult(
                False,
                f"User with role '{ctx.invitee.role.value}' "
                f"cannot be assigned project role '{ctx.target_role.value}'.",
            )

        return PermissionResult(True)

    @staticmethod
    def _get_allowed_project_roles_for_user(user_role: UserRole) -> set[ProjectRole]:
        if user_role.is_customer():
            return {ProjectRole.VIEWER, ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER}

        return {ProjectRole.VIEWER, ProjectRole.CONTRIBUTOR, ProjectRole.MANAGER}


class IsProjectOwnerOrManagerRule:
    """Участник должен являться владельцем или менеджером проекта"""

    def __init__(self, project_membership: ProjectMembership) -> None:
        self.project_membership = project_membership

    def check(self) -> PermissionResult:
        is_owner_or_manager = (
                self.project_membership.has_role(ProjectRole.OWNER)
                or self.project_membership.has_role(ProjectRole.MANAGER)
        )
        return (
            PermissionResult(True)
            if is_owner_or_manager
            else PermissionResult(False, "Not a project super user")
        )


class AddMemberByContributorRule(AuthorizationRule[AddMemberContext]):
    """
    Правило для добавления участника контрибьютором.
    """

    ALLOWED_TARGET_ROLES: ClassVar[set[ProjectRole]] = {
        ProjectRole.VIEWER, ProjectRole.CUSTOMER, ProjectRole.CONTRIBUTOR
    }

    @classmethod
    def check(cls, ctx: AddMemberContext) -> PermissionResult:
        if ctx.current_membership.project_role == ProjectRole.CONTRIBUTOR:
            if ctx.target_role not in cls.ALLOWED_TARGET_ROLES:
                return PermissionResult(
                    False,
                    "Project contributor can add only members with roles: "
                    f"{', '.join(cls.ALLOWED_TARGET_ROLES)}",
                )

            return PermissionResult(True)

        return PermissionResult(False, "Not a project contributor")


class AddMemberByCustomerManagerRule(AuthorizationRule[AddMemberContext]):
    """
    Менеджер со стороны клиента может добавлять только клиентов.
    """

    ALLOWED_TARGET_ROLES: ClassVar[set[ProjectRole]] = {
        ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER
    }

    @classmethod
    def check(cls, ctx: AddMemberContext) -> PermissionResult:
        if ctx.current_membership is not None and \
                ctx.current_membership.project_role == ProjectRole.CUSTOMER_MANAGER:
            if ctx.target_role not in cls.ALLOWED_TARGET_ROLES:
                return PermissionResult(
                    False,
                    f"Customer manager can add only members with roles: "
                    f"{', '.join(r.value for r in cls.ALLOWED_TARGET_ROLES)}",
                )

            return PermissionResult(True)

        return PermissionResult(False, "Not a customer manager")


class IsStaffMemberRule(AuthorizationRule[ProjectContext]):
    STAFF_PROJECT_ROLES: ClassVar[set[ProjectRole]] = {
        ProjectRole.CONTRIBUTOR, ProjectRole.MANAGER, ProjectRole.OWNER
    }

    @classmethod
    def check(cls, ctx: ProjectContext) -> PermissionResult:
        if ctx.current_membership is not None and \
                ctx.current_membership.project_role in cls.STAFF_PROJECT_ROLES:
            return PermissionResult(True)

        return PermissionResult(False, "Project staff required")


class CannotRemoveOwnerRule(AuthorizationRule[RemoveMemberContext]):
    @staticmethod
    def check(ctx: RemoveMemberContext) -> PermissionResult:
        if ctx.membership_to_remove.user_id == ctx.project.owner_id:
            return PermissionResult(False, "Cannot remove the project owner")

        return PermissionResult(True)


class IsManagerRule(AuthorizationRule[ProjectContext]):
    @staticmethod
    def check(ctx: ProjectContext) -> PermissionResult:
        if ctx.current_membership and ctx.current_membership.project_role == ProjectRole.OWNER:
            return PermissionResult(True)

        return PermissionResult(False, "Not a project manager")


CreateProjectRule = AllOf(HasAllowedCreationRoleRule, IsUserPrincipalRule)
ManageProjectRule = AllOf(MembershipExistsRule, IsStaffMemberRule)
AddMemberRule = AnyOf(
    IsOwnerOrAdminRule,
    AllOf(
        MembershipExistsRule,
        TargetRoleCompatibilityRule,
        AnyOf(AddMemberByContributorRule, AddMemberByCustomerManagerRule)
    )
)
RemoveMemberRule = AllOf(
    MembershipExistsRule,
    CannotRemoveOwnerRule,
    AnyOf(IsOwnerOrAdminRule, IsManagerRule)
)
