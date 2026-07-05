from .authz import PermissionResult, Subject, SubjectType
from .entities import Invitation, User
from .vo import UserRole


class HasAnyRoleRule:
    def __init__(self, subject: Subject, required_roles: list[UserRole]) -> None:
        self.subject = subject
        self.required_roles = required_roles

    def check(self) -> PermissionResult:
        if self.subject.has_any_role(self.required_roles):
            return PermissionResult(True)

        return PermissionResult(
            False, f"Required a least one role: {'; '.join(self.required_roles)}"
        )


class IsAdminRule:
    def __init__(self, subject: Subject | User) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.has_role(UserRole.ADMIN):
            return PermissionResult(True)

        return PermissionResult(False, "Admin required")


class IsStaffRule:
    def __init__(self, subject: Subject | User) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.has_any_role(UserRole.staff_roles()):
            return PermissionResult(True)

        return PermissionResult(False, "Require staff user")


class IsSupportRule:
    def __init__(self, subject: Subject | User) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.has_any_role(UserRole.support_roles()):
            return PermissionResult(True)

        return PermissionResult(False, "Require support user")


class IsCustomerRule:
    def __init__(self, subject: Subject | User) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.has_any_role(UserRole.customer_roles()):
            return PermissionResult(True)

        return PermissionResult(False, "Require customer user")


class IsUserRule:
    def __init__(self, subject: Subject) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.type == SubjectType.USER:
            return PermissionResult(True)

        return PermissionResult(False, "You are not user")


class IsInviterRule:
    def __init__(self, subject: Subject, invitation: Invitation) -> None:
        self.subject = subject
        self.invitation = invitation

    def check(self) -> PermissionResult:
        if self.invitation.invited_by != self.subject.id:
            return PermissionResult(False, "You are not inviter of this invitation")

        return PermissionResult(True)
