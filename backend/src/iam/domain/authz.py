from typing import Any, Protocol

from dataclasses import dataclass, field
from enum import StrEnum, auto
from uuid import UUID

from .vo import Email, UserRole


class SubjectType(StrEnum):
    USER = auto()  # пользователь (человек)
    CLIENT = auto()  # внешние интеграции (machine 2 machine)
    AI_AGENT = auto()


@dataclass(frozen=True)
class Subject:
    """
    Единый субъект авторизации в системе.
    Объединяет как обычных пользователей, так и внешние приложения.
    """

    id: UUID
    type: SubjectType

    scopes: list[str] = field(default_factory=list)  # для clients

    email: Email | None = None
    roles: list[UserRole] = field(default_factory=list)
    counterparty_id: UUID | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_user(self) -> bool:
        return self.type == SubjectType.USER

    @property
    def is_client(self) -> bool:
        return self.type == SubjectType.CLIENT

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


@dataclass(frozen=True)
class PermissionResult:
    allowed: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.allowed and self.reason is None:
            raise ValueError("Reason required, when not allowed")


class AuthorizationRule(Protocol):
    """
    Атомарное правило проверки прав доступа.
    Каждое правило реализует ровно один бизнес инвариант или условие безопасности.
    """

    def check(self) -> PermissionResult: ...


class AllOf:
    """
    Стратегия при которой ВСЕ правила должны выполниться.
    Возвращает первую возникшую ошибку (важен порядок).
    """

    def __init__(self, *rules: AuthorizationRule) -> None:
        self._rules = rules

    def check(self) -> PermissionResult:
        for rule in self._rules:
            permission = rule.check()
            if not permission.allowed:
                return permission

        return PermissionResult(True)


class AnyOf:
    """
    Стратегия при которой должно выполниться ХОТЯ БЫ ОДНО правило.
    Возвращает ошибку, если не выполнилось ни одно условие (копит ошибки).
    Важен порядок, так как выводится последнее сообщение об ошибке.
    """

    def __init__(self, *rules: AuthorizationRule) -> None:
        self._rules = rules

    def check(self) -> PermissionResult:
        reasons: list[str] = []

        for rule in self._rules:
            permission = rule.check()
            if permission.allowed:
                return permission

            reasons.append(permission.reason)

        final_reason = reasons[-1] if reasons else "Access denied"
        return PermissionResult(False, final_reason)


class IsAdminRule:
    def __init__(self, subject: Subject) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.has_role(UserRole.ADMIN):
            return PermissionResult(True)

        return PermissionResult(False, "Admin required")
