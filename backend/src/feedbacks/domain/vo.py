from dataclasses import dataclass
from typing import ClassVar

from src.shared.domain.vo import ValueObject


@dataclass(frozen=True)
class FeedbackRating(ValueObject):
    """
    Оценка качества обслуживания по отзыву.
    """

    MIN_VALUE: ClassVar[int] = 1
    MAX_VALUE: ClassVar[int] = 5

    value: int

    def __post_init__(self) -> None:
        if not self.MIN_VALUE <= self.value <= self.MAX_VALUE:
            raise ValueError(f"Feedback rating must be between {self.MIN_VALUE} and {self.MAX_VALUE}")