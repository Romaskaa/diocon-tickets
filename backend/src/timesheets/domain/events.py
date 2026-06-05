from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from ...shared.domain.events import Event


@dataclass(frozen=True, kw_only=True)
class WorklogCreated(Event):
    """Создана запись о потраченном времени"""

    worklog_id: UUID
    ticket_id: UUID | None = None
    task_id: UUID | None = None
    user_id: UUID
    hours_spent: Decimal
    entry_date: date


@dataclass(frozen=True, kw_only=True)
class WorklogSubmitted(Event):
    """Запись отправлена на согласование"""

    worklog_id: UUID
    ticket_id: UUID | None = None
    task_id: UUID | None = None
    user_id: UUID
    hours_spent: Decimal


@dataclass(frozen=True, kw_only=True)
class WorklogApproved(Event):
    """Потраченные часы согласованы"""

    worklog_id: UUID
    ticket_id: UUID | None = None
    task_id: UUID | None = None
    user_id: UUID
    hours_spent: Decimal
    entry_date: date
    approved_by: UUID


@dataclass(frozen=True, kw_only=True)
class WorklogRejected(Event):
    """Запись отклонена"""

    worklog_id: UUID
    rejected_by: UUID
    hours_spent: Decimal
    reason: str

# =================================== События для ЛУРВ ===================================


@dataclass(frozen=True, kw_only=True)
class TimesheetSubmitted(Event):
    """ЛУРВ отправлен на согласование"""

    timesheet_id: UUID
    user_id: UUID
    total_hours: Decimal
    submitted_at: date


@dataclass(frozen=True, kw_only=True)
class TimesheetApproved(Event):
    """ЛУРВ согласован"""

    timesheet_id: UUID
    approved_by: UUID
    approved_at: date
    total_hours: Decimal


@dataclass(frozen=True, kw_only=True)
class TimesheetRejected(Event):
    """ЛУРВ отклонён"""

    timesheet_id: UUID
    rejected_by: UUID
    reason: str
