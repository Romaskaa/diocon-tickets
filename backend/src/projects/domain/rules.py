"""
Реализация правил для авторизации.
"""

from typing import ClassVar

from collections.abc import Mapping

from src.iam.domain.authz import AnyOf, PermissionResult
from src.iam.domain.entities import User

from .entities import ProjectMember
from .vo import ProjectRole


class IsProjectStaffRule:
    ALLOWED_PROJECT_ROLES: ClassVar[set[ProjectRole]] = {
        ProjectRole.CONTRIBUTOR, ProjectRole.MANAGER, ProjectRole.OWNER
    }

    def __init__(self, membership: ProjectMember | None = None) -> None:
        self.membership = membership

    def check(self) -> PermissionResult:
        if self.membership is None:
            return PermissionResult(False, "You are not member of this project")

        for allowed_project_role in self.ALLOWED_PROJECT_ROLES:
            if self.membership.has_role(allowed_project_role):
                return PermissionResult(True)

        return PermissionResult(
            False,
            "Project project_role must be one of: "
            f"{', '.join(r.value for r in self.ALLOWED_PROJECT_ROLES)}",
        )


class IsMemberExistsRule:

    def __init__(self, member: ProjectMember | None) -> None:
        self.member = member

    def check(self) -> PermissionResult:
        if self.member is None:
            return PermissionResult(False, "You are not member of the project")

        return PermissionResult(True)


class IsProjectOwnerRule:
    def __init__(self, member: ProjectMember) -> None:
        self.member = member

    def check(self) -> PermissionResult:
        if self.member.has_role(ProjectRole.OWNER):
            return PermissionResult(True)

        return PermissionResult(False, "You are not owner of this project")


class IsProjectManagerRule:
    def __init__(self, member: ProjectMember) -> None:
        self.member = member

    def check(self) -> PermissionResult:
        if self.member.has_role(ProjectRole.MANAGER):
            return PermissionResult(True)

        return PermissionResult(False, "You are not manager of this project")


class IsProjectOwnerOrManagerRule:
    def __init__(self, member: ProjectMember) -> None:
        self.member = member

    def check(self) -> PermissionResult:
        policy = AnyOf(
            IsProjectManagerRule(self.member),
            IsProjectOwnerRule(self.member),
        )
        return policy.check()


class GrantProjectRoleRule:
    """
    Проверка валидности назначенной проектной роли добавленному участнику.
    """

    def __init__(self, invitee: User, target_roles: set[ProjectRole]) -> None:
        self.invitee = invitee
        self.target_roles = target_roles

    def check(self) -> PermissionResult:
        if ProjectRole.OWNER in self.target_roles:
            return PermissionResult(
                False, "OWNER project_role cannot be assigned through membership addition"
            )

        allowed_roles = set()
        for invitee_role in self.invitee.roles:
            if invitee_role.is_customer:
                allowed_roles.update(ProjectRole.customer_roles())
            else:
                roles = ProjectRole.staff_roles() | ProjectRole.customer_roles()
                allowed_roles.update(roles)

        for target_role in self.target_roles:
            if target_role not in allowed_roles:
                return PermissionResult(
                    False,
                    f"User with roles: {', '.join(self.invitee.roles)}, "
                    f"cannot be granted project role '{target_role.value}'.",
                )

        return PermissionResult(True)


class TargetRoleAssignmentRule:
    ASSIGNMENT_MATRIX: ClassVar[Mapping[ProjectRole, set[ProjectRole]]] = {
        ProjectRole.CONTRIBUTOR: {
            ProjectRole.VIEWER,
            ProjectRole.CUSTOMER,
            ProjectRole.CONTRIBUTOR,
        },
        ProjectRole.CUSTOMER_MANAGER: {
            ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER
        },
        ProjectRole.MANAGER: set(ProjectRole) - {ProjectRole.OWNER},
        ProjectRole.OWNER: set(ProjectRole) - {ProjectRole.OWNER},
        ProjectRole.CUSTOMER: set(),
        ProjectRole.VIEWER: set(),
    }

    def __init__(self, actor_member: ProjectMember, target_roles: set[ProjectRole]) -> None:
        self.actor_member = actor_member
        self.target_roles = target_roles

    def check(self) -> PermissionResult:
        allowed_roles = set()
        for project_role in self.actor_member.project_roles:
            allowed_roles.update(self.ASSIGNMENT_MATRIX.get(project_role, set()))

        if not allowed_roles:
            return PermissionResult(False, "You have no permission to assign any project roles")

        if not self.target_roles.issubset(allowed_roles):
            denied_roles = self.target_roles - allowed_roles
            return PermissionResult(
                False,
                f"Your project roles "
                f"({', '.join(role.value for role in self.actor_member.project_roles)}) "
                f"do not allow assigning: {', '.join(role.value for role in denied_roles)}",
            )

        return PermissionResult(True)
