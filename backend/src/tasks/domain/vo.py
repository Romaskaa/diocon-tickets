from typing import ClassVar

from dataclasses import dataclass
from enum import StrEnum

from ...shared.domain.vo import ValueObject


class TaskStatus(StrEnum):
    """Статус выполнения задачи"""

    BACKLOG = "backlog"  # ещё сырая задача
    TODO = "todo"  # готова к выполнению
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class StoryPoints(ValueObject):
    """
    """

    ALLOWED_VALUES: ClassVar[set[int]] = {1, 2, 3, 5, 8, 13, 21}

    value: int

    def __post_init__(self) -> None:
        if self.value not in self.ALLOWED_VALUES:
            raise ValueError(
                f"Invalid story point value: {self.value}. "
                f"Use numbers from a series: {self.ALLOWED_VALUES}"
            )

    def __str__(self) -> str:
        return f"{self.value} SP"
