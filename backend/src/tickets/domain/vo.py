from typing import ClassVar, Self

import re
from dataclasses import dataclass, field
from enum import StrEnum

from ...shared.domain.vo import ValueObject
from ...shared.utils.text import get_latin_slug
from ...shared.utils.time import current_datetime


class TicketStatus(StrEnum):
    """Возможные статусы тикета"""

    # Начальные статусы
    NEW = "Новый"
    PENDING_APPROVAL = "На согласовании"

    # Рабочие статусы
    OPEN = "Открыт"
    IN_PROGRESS = "В работе"
    WAITING = "Ожидает ответа"

    # Завершающие статусы
    RESOLVED = "Решён"
    CLOSED = "Закрыт"
    REOPENED = "Переоткрыт"

    # Дополнительные
    REJECTED = "Отклонён"
    CANCELED = "Отменён"


class TicketPriority(StrEnum):
    """Приоритет тикета"""

    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"
    CRITICAL = "Критический"  # Время реакции поддержки - мгновенное


@dataclass(frozen=True, kw_only=True)
class Tag(ValueObject):
    """
    Теги - метки (ключевые слова), которые можно присваивать тикетам для дополнительной,
    неструктурированной классификации.
    """

    name: str
    color: str = field(default="#3498db")

    def __str__(self) -> str:
        return self.name


class CommentType(StrEnum):
    """Тип комментария"""

    PUBLIC = "public"  # виден всем
    INTERNAL = "internal"  # виден только сотрудникам поддержки
    NOTE = "note"  # виден только автору


class ProjectStatus(StrEnum):
    """Статус проекта"""

    ACTIVE = "active"
    ON_HOLD = "on_hold"  # На удержании
    ARCHIVED = "archived"
    COMPLETED = "completed"


class ProjectRole(StrEnum):
    """Роли внутри конкретного проекта"""

    OWNER = "owner"  # Полный контроль над проектом
    MANAGER = "manager"  # Может управлять участниками, настройками
    MEMBER = "member"  # Обычный участник (агент, разработчик)
    VIEWER = "viewer"  # Только просмотр
    CUSTOMER = "customer"  # Обычный клиент
    CUSTOMER_ADMIN = "customer_admin"  # Администратор со стороны клиента


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


@dataclass(frozen=True)
class TicketNumber(ValueObject):
    """
    Уникальный номер тикета в формате - PREFIX-YY-SEQUENCE

    Примеры:
     - РОМASHKA-26-00012456
     - INT-26-00004521
     - YANDEXT-26-00123769
    """

    INTERNAL_PREFIX: ClassVar[str] = "INT"
    MAX_PREFIX_LENGTH: ClassVar[int] = 10  # Максимальная длина префикса
    MIN_PREFIX_LENGTH: ClassVar[int] = 1
    SEQUENCE_LENGTH: ClassVar[int] = 8
    YEAR_LENGTH: ClassVar[int] = 2
    PREFIX_LENGTH: ClassVar[int] = 3
    NUMBER_PARTS: ClassVar[int] = 3

    value: str

    def __post_init__(self) -> None:

        # 1. Номер не должен быть пустым
        if not self.value.strip():
            raise ValueError("Ticket number cannot be empty")

        # 2. Проверка формата
        if not self._is_valid_format(self.value):
            raise ValueError(
                f"Invalid ticket number format: {self.value}. "
                f"Expected: PREFIX-YY-NNNNNNNN (e.g: ROMASHKA-26-00012345)"
            )

    @classmethod
    def _is_valid_format(cls, number: str) -> bool:
        """Проверка формата PREFIX-YY-NNNNNNNN"""

        if len(number) > cls.MAX_PREFIX_LENGTH + 1 + cls.YEAR_LENGTH + 1 + cls.SEQUENCE_LENGTH:
            return False

        parts = number.split("-")
        if len(parts) != cls.NUMBER_PARTS:
            return False

        prefix, year, seq = parts

        return (
            cls._is_valid_prefix(prefix)
            and len(year) == cls.YEAR_LENGTH
            and year.isdigit()
            and len(seq) == cls.SEQUENCE_LENGTH
            and seq.isdigit()
        )

    @classmethod
    def _is_valid_prefix(cls, prefix: str) -> bool:
        """Префикс должен состоять только из заглавных латинских букв и цифр"""

        if not cls.MIN_PREFIX_LENGTH <= len(prefix) <= cls.MAX_PREFIX_LENGTH:
            return False
        return bool(re.fullmatch(r"[A-Z0-9]+", prefix))

    @classmethod
    def create(
            cls,
            total_tickets: int,
            /,
            project_key: ProjectKey | None = None,
            counterparty_name: str | None = None,
    ) -> Self:
        """Генерация уникального номера для тикета"""

        # 1. Проверка количества тикетов + валидация входных параметров
        if total_tickets < 0:
            raise ValueError("Total tickets cannot be negative")

        if project_key is not None and counterparty_name is not None:
            raise ValueError("Only one of the project key or counterparty name must be specified")

        # 2. Определение префикса
        if project_key is not None:
            prefix = project_key.value
        elif counterparty_name is not None:
            # Транслитерация и нормализация префикса
            slug = get_latin_slug(counterparty_name, upper=True)
            prefix = slug[: cls.MAX_PREFIX_LENGTH]
        else:
            # Если ни проект, ни контрагент не указан, то тикет внутренний
            prefix = cls.INTERNAL_PREFIX

        # 3. Год (две последние цифры)
        year_short = current_datetime().year % 100

        # 4. Числовая последовательность, последние 8 цифр
        sequence = f"{total_tickets + 1}".zfill(cls.SEQUENCE_LENGTH)

        # 5. Формирование номера
        number = f"{prefix}-{year_short:02d}-{sequence}"
        return cls(value=number)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"TicketNumber({self.value!r})"

    @property
    def prefix(self) -> str:
        """Префикс (РОМ, INT, ЯНД и т.д.)"""

        return self.value.split("-")[0]

    @property
    def year_short(self) -> int:
        """Год (две последние цифры)"""

        return int(self.value.split("-")[1])

    @property
    def sequence(self) -> str:
        """Порядковый номер"""

        return self.value.split("-")[2]

    @property
    def is_internal(self) -> bool:
        """Является ли тикет внутренним"""

        return self.prefix == self.INTERNAL_PREFIX


class ReactionType(StrEnum):
    """
    Тип реакции, которая оставлена к комментарию
    """

    LIKE = "like"  # 👍
    THANKS = "thanks"  # 🙏
    IN_PROGRESS = "in_progress"  # 👀
    RESOLVED = "resolved"  # 🚀
    IMPORTANT = "important"  # ❗
