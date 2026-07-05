from typing import ClassVar, Self

import re
from dataclasses import dataclass, field
from enum import StrEnum, auto

from email_validator import EmailNotValidError, validate_email

from src.shared.domain.vo import ValueObject


class UserRole(StrEnum):
    """Роли пользователей"""

    # Клиентские
    CUSTOMER_ADMIN = auto()  # администратор клиентской стороны
    CUSTOMER = auto()  # клиент / обычный пользователь

    # Команда поддержки
    SUPPORT_AGENT = auto()  # сотрудник поддержки (1 линия)
    SUPPORT_MANAGER = auto()  # старший сотрудник поддержки (team lead)

    # Команда разработки
    DEVELOPER = auto()

    # Бизнес роли
    ACCOUNT_MANAGER = auto()
    FINANCE = auto()

    ADMIN = auto()  # системный администратор

    @property
    def is_customer(self) -> bool:
        return self.value in {self.CUSTOMER, self.CUSTOMER_ADMIN}

    @property
    def is_support(self) -> bool:
        return self.value in {self.SUPPORT_AGENT, self.SUPPORT_MANAGER, self.ADMIN}

    @property
    def is_staff(self) -> bool:
        return self.value not in {self.CUSTOMER, self.CUSTOMER_ADMIN}

    @classmethod
    def staff_roles(cls) -> set[Self]:
        return {
            cls.ADMIN,
            cls.SUPPORT_MANAGER,
            cls.SUPPORT_AGENT,
            cls.DEVELOPER,
            cls.ACCOUNT_MANAGER,
            cls.FINANCE,
        }

    @classmethod
    def support_roles(cls) -> set[Self]:
        return {cls.SUPPORT_AGENT, cls.SUPPORT_MANAGER}

    @classmethod
    def customer_roles(cls) -> set[Self]:
        return {cls.CUSTOMER, cls.CUSTOMER_ADMIN}


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
                "Cannot planned_start or planned_end with a special character, "
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


@dataclass(frozen=True, slots=True)
class Email:
    value: str = field(compare=True, hash=True)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Email cannot be empty")

        try:
            validation = validate_email(self.value, check_deliverability=False)
            normalized = validation.normalized
        except EmailNotValidError as e:
            raise ValueError("Invalid email address") from e

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Email({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Email):
            return self.value == other.value

        if isinstance(other, str):
            try:
                validation = validate_email(self.value, check_deliverability=False)
            except EmailNotValidError:
                return False
            else:
                return self.value == validation.normalized

        return NotImplemented

    @property
    def domain(self) -> str:
        return self.value.split("@")[-1]


@dataclass(frozen=True, slots=True)
class PasswordHash(ValueObject):
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Password hash cannot be empty")

    def __repr__(self) -> str:
        return "PasswordHash(******)"

    def __str__(self) -> str:
        return "******"

    def get_hashed_value(self) -> str:
        return self.value
