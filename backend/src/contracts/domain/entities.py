from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from ...shared.domain.entities import AggregateRoot, Entity
from ...shared.domain.exceptions import InvariantViolationError
from ...shared.utils.time import current_datetime
from .events import (
    ContractClosed,
    ContractPackageAdded,
    ContractReactivated,
    ContractSuspended,
    HoursConsumed,
)
from .vo import ContractStatus, ContractType, EstimationMethod, HoursPackageType


@dataclass(kw_only=True)
class ContractHoursPackage(Entity):
    """
    Пакет оплаченных часов в рамках договора
    """

    contract_id: UUID
    package_type: HoursPackageType
    hours: Decimal
    start_date: date
    end_date: date | None = None
    consumed_hours: Decimal = Decimal(0)

    @property
    def remaining_hours(self) -> Decimal:
        """Оставшиеся часы"""

        return self.hours - self.consumed_hours


@dataclass(kw_only=True)
class ServiceContract(AggregateRoot):
    """
    Сервисный договор с контрагентом
    """

    contract_number: str
    counterparty_id: UUID
    start_date: date
    end_date: date | None = None

    # Всего оплачено часов
    total_hours: Decimal
    # Часов уже потрачено
    consumed_hours: Decimal = field(default=Decimal(0))
    # Оставшиеся часы
    remaining_hours: Decimal = field(init=False)

    status: ContractStatus
    contract_type: ContractType

    # Пакеты часов (может быть несколько)
    packages: list[ContractHoursPackage] = field(default_factory=list)

    created_by: UUID

    def __post_init__(self) -> None:
        # 1. Количество часов никогда не может быть отрицательным
        if self.total_hours <= 0:
            raise ValueError("Total hours must be positive")

        if self.consumed_hours < 0:
            raise ValueError("Consumed hours cannot be negative")

        # 2. Расчёт оставшихся часов
        self.remaining_hours = self.total_hours - self.consumed_hours
        if self.remaining_hours < 0:
            raise InvariantViolationError("Consumed hours cannot exceed total hours")

        # 3. Дата окончания не может быть раньше даты начала
        if self.end_date is not None and self.end_date < self.start_date:
            raise InvariantViolationError("End date cannot be before start date")

    def add_package(
            self,
            package_type: HoursPackageType,
            hours: Decimal,
            start_date: date,
            added_by: UUID,
            end_date: date | None = None,
    ) -> None:
        """Добавление нового пакета часов"""

        # 1. Количество часов должно быть положительным числом
        if hours <= 0:
            raise ValueError("Package hours must be positive")

        # 2. Добавление пакета
        package = ContractHoursPackage(
            contract_id=self.id,
            package_type=package_type,
            hours=hours,
            start_date=start_date,
            end_date=end_date,
        )
        self.packages.append(package)
        self.total_hours += hours
        self.remaining_hours = self.total_hours - self.consumed_hours
        self.updated_at = current_datetime()

        # 3. Регистрация доменного события
        self.register_event(
            ContractPackageAdded(
                contract_id=self.id,
                package_type=package_type,
                hours=float(hours),
                added_by=added_by,
            )
        )

    def consume_hours(self, hours: Decimal, ticket_id: UUID, user_id: UUID) -> None:
        """Списание часов при выполнении работ"""

        # 1. Нельзя списать отрицательно кол-во часов
        if hours < 0:
            raise ValueError("Hours must be positive")

        # 2. Количество списанных часов не может быть больше, чем кол-во оставшихся часов
        if self.remaining_hours < hours:
            raise InvariantViolationError("Not enough remaining hours on contract")

        # 3. Обновление значений
        self.consumed_hours += hours
        self.remaining_hours = self.total_hours - self.consumed_hours
        self.updated_at = current_datetime()

        # 4. Регистрация доменного события
        self.register_event(
            HoursConsumed(
                contract_id=self.id,
                ticket_id=ticket_id,
                user_id=user_id,
                hours=float(hours),
                remaining_hours=float(self.remaining_hours),
            )
        )

    def suspend(self, reason: str, suspended_by: UUID) -> None:
        """Приостановка договора (например, из-за задолженности)"""

        if self.status != ContractStatus.ACTIVE:
            return

        self.status = ContractStatus.SUSPENDED
        self.updated_at = current_datetime()

        self.register_event(
            ContractSuspended(
                contract_id=self.id,
                reason=reason,
                suspended_by=suspended_by,
            )
        )

    def reactivate(self, reactivated_by: UUID) -> None:
        """Возобновление договора"""

        if self.status != ContractStatus.SUSPENDED:
            return

        self.status = ContractStatus.ACTIVE
        self.updated_at = current_datetime()

        self.register_event(
            ContractReactivated(contract_id=self.id, reactivated_by=reactivated_by)
        )

    def close(self, closed_by: UUID) -> None:
        """Закрытие договора"""

        self.status = ContractStatus.COMPLETED
        self.updated_at = current_datetime()

        self.register_event(ContractClosed(contract_id=self.id, closed_by=closed_by))


@dataclass(kw_only=True)
class TicketEffortEstimate(Entity):
    """
    Предварительная оценка трудозатрат по тикету
    """

    ticket_id: UUID

    # Основная оценка
    estimated_hours: Decimal
    confidence: float = field(default=0.0)

    # Кто и как оценил
    method: EstimationMethod
    estimated_by: UUID | None = None
    ai_model: str | None = None

    # Дополнительно
    notes: str | None = None
