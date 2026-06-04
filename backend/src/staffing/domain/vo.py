from typing import ClassVar

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from ...shared.domain.vo import ValueObject


class SkillLevel(StrEnum):
    """Уровни оценки навыков сотрудника"""

    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    EXPERT = "expert"


@dataclass(frozen=True)
class Skill(ValueObject):
    """Навык сотрудника"""

    MIN_NAME_LENGTH: ClassVar[int] = 2
    MAX_NAME_LENGTH: ClassVar[int] = 100

    name: str
    level: SkillLevel
    years_experience: int | None = None

    def __post_init__(self) -> None:
        # 1. Валидация длины названия навыка
        if not self.name.strip():
            raise ValueError("Skill name cannot be empty")

        if not (self.MIN_NAME_LENGTH <= len(self.name) <= self.MAX_NAME_LENGTH):
            raise ValueError(
                f"Skill name must be between {self.MIN_NAME_LENGTH} and {self.MAX_NAME_LENGTH}"
            )

        # 2. Количество лет опыта не может быть меньше 0
        if self.years_experience < 0:
            raise ValueError("Skill years experience cannot be negative")


class SupportLineLevel(StrEnum):
    """Уровни линий поддержки"""

    L1 = "L1"  # 1 линия
    L2 = "L2"
    L3 = "L3"  # 3 линия (эксперты)


class TicketAssignmentSuggestionStatus(StrEnum):
    """Статус рекомендации кандидата"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TicketAssigneeCandidate(ValueObject):
    """
    Сотрудник (кандидат) наиболее подходящий для работы с тикетом
    """

    user_id: UUID
    full_name: str
    match_score: float
    matching_reason: str
