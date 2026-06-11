from typing import ClassVar

import re
from dataclasses import dataclass
from enum import StrEnum, auto

from ...shared.domain.vo import ValueObject


class ProjectStatus(StrEnum):
    """Статус проекта"""

    ACTIVE = auto()
    ON_HOLD = auto()  # На удержании
    ARCHIVED = auto()
    COMPLETED = auto()


class ProjectStageStatus(StrEnum):
    """Статус этапа проекта"""

    PLANNED = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    ON_HOLD = auto()  # Приостановлен
    SKIPPED = auto()  # Пропущен


class ProjectRole(StrEnum):
    """Роли внутри конкретного проекта"""

    OWNER = "owner"  # Полный контроль над проектом
    MANAGER = "manager"  # Может управлять участниками, настройками
    CONTRIBUTOR = "contributor"  # Обычный участник (агент, разработчик)
    VIEWER = "viewer"  # только просмотр (аудитор)
    CUSTOMER = "customer"  # клиент (принадлежит контрагенту)
    CUSTOMER_MANAGER = "customer_manager"  # расширенные права (менеджер со стороны клиента)


@dataclass(frozen=True)
class ProjectKey(ValueObject):
    """
    Уникальный ключ проекта.

    Формат:
     - Длина от 2 до 10 символов
     - Только заглавные латинские буквы (A-Z) и цифры (0-9)
     - Первый символ — обязательно буква
     - Без пробелов, дефисов, подчёркиваний и других разделителей

    Примеры: "PRJ", "MOB_APP", "BACKEND1", "PROEKT"
    """

    PATTERN: ClassVar[re.Pattern] = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")

    value: str

    def __post_init__(self) -> None:
        # 1. Ключ не может быть пустым
        if not self.value:
            raise ValueError("Project key cannot be empty")

        # 2. Нормализация строки
        cleaned = re.sub(r"[^A-Za-z0-9]", "", self.value.upper().strip())
        if not self.PATTERN.match(cleaned):
            raise ValueError(
                f"Invalid project key format: '{self.value}'. "
                "Key must be 2-10 characters long, start with a letter (A-Z), "
                "and contain only letters and digits (no spaces, underscores, or Cyrillic)."
            )

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ProjectKey('{self.value}')"
