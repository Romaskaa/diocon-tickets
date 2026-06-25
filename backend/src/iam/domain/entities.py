import secrets
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from pydantic import SecretStr

from src.shared.domain.entities import Entity
from src.shared.domain.exceptions import InvariantViolationError
from src.shared.utils.time import current_datetime

from .vo import Email, FullName, Username, UserRole


@dataclass(kw_only=True)
class User(Entity):
    """
    Пользователь системы (человек).
    """

    email: Email
    username: Username | None = None
    full_name: FullName | None = None
    avatar_url: str | None = None
    roles: set[UserRole]
    counterparty_id: UUID | None = None
    password_hash: SecretStr
    is_active: bool = True

    def __post_init__(self) -> None:
        """Проверка инвариантов"""

        # Клиенты должны быть привязаны к контрагенту
        if self.counterparty_id is None and \
                self.role in {UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN}:
            raise InvariantViolationError("Counterparty must be specified for clients")

        # Сотрудники поддержки не должны иметь прямой связи с контрагентом
        if self.role.is_support() and self.counterparty_id is not None:
            raise InvariantViolationError("Support users should not have direct counterparty_id")

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles


def generate_invite_token(length: int = 32) -> str:
    """Генерация токена для активации приглашения"""

    return secrets.token_urlsafe(length)


@dataclass(kw_only=True)
class Invitation(Entity):
    """
    Приглашение в тикет систему для нового пользователя
    """

    email: Email
    token: str = field(default_factory=generate_invite_token)
    invited_by: UUID
    assigned_role: UserRole
    counterparty_id: UUID | None = None
    expires_at: datetime
    used_at: datetime | None = None
    is_used: bool = False

    def __post_init__(self) -> None:

        # 1. У клиентов должен быть указан контрагент
        if self.assigned_role in {UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN} \
                and self.counterparty_id is None:
            raise InvariantViolationError(
                "For invitations to clients, you must specify a counterparty ID"
            )

        # 2. Для сотрудников поддержки не нужно указывать контрагента
        if self.assigned_role in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER} \
                and self.counterparty_id is not None:
            raise InvariantViolationError(
                "For internal employees, counterparty ID does not need to be specified"
            )

    @property
    def is_valid(self) -> bool:
        """Актуально ли приглашение"""

        return not self.is_used and self.expires_at > current_datetime()

    def mark_as_used(self) -> None:
        """Пометить, как использованное"""

        self.used_at = current_datetime()
        self.is_used = True
