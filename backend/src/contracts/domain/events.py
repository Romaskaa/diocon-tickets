from dataclasses import dataclass
from uuid import UUID

from ...shared.domain.events import Event
from .vo import HoursPackageType


@dataclass(frozen=True, kw_only=True)
class HoursConsumed(Event):
    """Часы списаны"""

    contract_id: UUID
    ticket_id: UUID
    user_id: UUID
    hours: float
    remaining_hours: float


@dataclass(frozen=True, kw_only=True)
class ContractPackageAdded(Event):
    """Добавлен новый пакет часов"""

    contract_id: UUID
    package_type: HoursPackageType
    hours: float
    added_by: UUID


@dataclass(frozen=True, kw_only=True)
class ContractSuspended(Event):
    """Договор приостановлен"""

    contract_id: UUID
    reason: str
    suspended_by: UUID


@dataclass(frozen=True, kw_only=True)
class ContractReactivated(Event):
    """Договор возобновлён"""

    contract_id: UUID
    reactivated_by: UUID


@dataclass(frozen=True, kw_only=True)
class ContractClosed(Event):
    """Договор закрыт"""

    contract_id: UUID
    closed_by: UUID
