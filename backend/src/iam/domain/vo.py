from typing import ClassVar

import re
from dataclasses import dataclass, field
from enum import StrEnum

from ...shared.domain.vo import ValueObject


class UserRole(StrEnum):
    """Роли пользователей"""

    # Клиентские
    CUSTOMER_ADMIN = "customer_admin"  # администратор клиентской стороны
    CUSTOMER = "customer"  # клиент / обычный пользователь

    # Команда поддержки
    SUPPORT_AGENT = "support_agent"  # сотрудник поддержки (1 линия)
    SUPPORT_MANAGER = "support_manager"  # старший сотрудник поддержки (team lead)

    # Работа с договорами и клиентами
    ACCOUNT_MANAGER = "account_manager"
    FINANCE = "finance"

    ADMIN = "admin"  # системный администратор

    def is_customer(self) -> bool:
        """Является ли клиентом"""

        return self.value in {self.CUSTOMER, self.CUSTOMER_ADMIN}

    def is_support(self) -> bool:
        """Является ли поддержкой"""

        return self.value in {self.SUPPORT_AGENT, self.SUPPORT_MANAGER, self.ADMIN}

    def is_internal(self) -> bool:
        """Является ли роль внутренней"""

        return self.value not in {self.CUSTOMER, self.CUSTOMER_ADMIN}


@dataclass(frozen=True, slots=True)
class FullName(ValueObject):
    """
    ФИО - доменный примитив для валидации российских имён
    """

    MIN_PARTS: ClassVar[int] = 2
    MAX_LENGTH: ClassVar[int] = 155

    value: str = field(compare=True, hash=True)

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Full name cannot be empty")

        if len(self.value) >= self.MAX_LENGTH:
            raise ValueError("Full name cannot be longer than 155 characters")

        parts = [part.strip() for part in self.value.split() if part.strip()]
        if len(parts) < self.MIN_PARTS:
            raise ValueError("Must have at least first and last name")

        pattern = re.compile(r"^[A-Za-zА-Яа-яЁё\s\-'’]+$")
        if not all(pattern.match(p) for p in parts):
            raise ValueError(f"Invalid characters in full name: {self.value!r}")

        normalized_parts = [p.title() for p in parts]
        normalized = " ".join(normalized_parts)

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"FullName({self.value!r})"

    def __eq__(self, other) -> bool:
        if isinstance(other, FullName):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other.strip().title()
        return NotImplemented

    @property
    def _parts(self) -> list[str]:
        return self.value.split()

    @property
    def last_name(self) -> str:
        """Фамилия (вторая часть)"""

        return self._parts[-1]

    @property
    def first_name(self) -> str:
        """Имя (первая часть)"""

        return self._parts[0]

    @property
    def middle_name(self) -> str | None:
        """Отчество"""

        if len(self._parts) > self.MIN_PARTS:
            return " ".join(self._parts[1:-1])
        return None


@dataclass(frozen=True, slots=True)
class Username(ValueObject):
    """
    Доменный примитив — имя пользователя (логин).

    Характеристики:
    - 3–30 символов
    - разрешены: a-z, 0-9, _,., —
    - не начинается и не заканчивается на _,., —
    - не содержит два подряд специальных символа (_,., —)
    - хранится и сравнивается в нижнем регистре
    """

    MIN_LENGTH: ClassVar[int] = 3
    MAX_LENGTH: ClassVar[int] = 30

    # Что проверяет это регулярное выражение:
    # - начинается и заканчивается буквой или цифрой
    # - внутри: буквы, цифры, и не более одного спецсимвола подряд
    PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[a-zа-яё0-9](?:(?![._-]{2})[a-zа-яё0-9._-])*[a-zа-яё0-9]$", re.IGNORECASE
    )

    value: str = field(compare=True, hash=True, repr=False)

    def __post_init__(self) -> None:

        cleaned = self.value.strip().lower()

        if not cleaned:
            raise ValueError("Username cannot be empty")

        if len(cleaned) < self.MIN_LENGTH:
            raise ValueError(f"Username too short (minimum {self.MIN_LENGTH} characters)")

        if len(cleaned) > self.MAX_LENGTH:
            raise ValueError(f"Username too long (max {self.MAX_LENGTH} characters)")

        if not self.PATTERN.match(cleaned):
            raise ValueError(
                "Username can only contains letters, numbers, periods, hyphens and underscores. "
                "Cannot start or end with a special character, "
                "cannot contain two special characters in a row."
            )

        if cleaned.isdigit():
            raise ValueError("Username cannot contains only digits")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Username({self.value!r})"

    def __eq__(self, other) -> bool:
        if isinstance(other, Username):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other.strip().lower()
        return NotImplemented
