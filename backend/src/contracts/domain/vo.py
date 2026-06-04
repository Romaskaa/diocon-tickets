from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from ...shared.domain.vo import ValueObject


class ContractStatus(StrEnum):
    """Статус договора"""

    DRAFT = "draft"  # черновик
    ACTIVE = "active"
    SUSPENDED = "suspended"  # приостановлен
    EXPIRED = "expired"  # срок истёк
    COMPLETED = "completed"  # завершён (все часы использованы или договор закрыт)


class ContractType(StrEnum):
    """Вид заключённого договора"""

    SUBSCRIPTION = "subscription"  # абонентская плата
    PREPAID = "prepaid"  # предоплаченные часы
    TIME_AND_MATERIALS = "time_and_materials"
    HYBRID = "hybrid"


class HoursPackageType(StrEnum):
    """Виды пакетов оплаченных часов"""

    MONTHLY = "monthly"  # ежемесячная
    QUARTERLY = "quarterly"  # поквартальная
    YEARLY = "yearly"  # годовая
    ONE_TIME = "one_time"  # единоразовый


class EstimationMethod(StrEnum):
    """Метод оценки трудозатрат по тикетам"""

    MANUAL = "manual"  # оценено человеком
    AI = "ai"  # с помощью AI


@dataclass(frozen=True, slots=True)
class NonNegativeDecimal(ValueObject):
    """
    Не отрицательное число (для точных значений: счета, часы, ...)
    """

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(f"{self.value}"))

        if self.value <= 0:
            raise ValueError(f"Value must be positive, got {self.value}")

    def __mul__(self, other) -> "NonNegativeDecimal":
        if isinstance(other, (int, Decimal)):
            return NonNegativeDecimal(self.value * other)

        return NotImplemented

    def __str__(self) -> str:
        return f"{self.value}"
