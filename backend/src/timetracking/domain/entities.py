from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from ...shared.domain.entities import AggregateRoot, Entity
from ...shared.domain.exceptions import InvalidStateError, InvariantViolationError
from ...shared.utils.time import current_datetime
from .events import (
    TimesheetApproved,
    TimesheetRejected,
    TimesheetSubmitted,
    WorklogApproved,
    WorklogCreated,
    WorklogRejected,
    WorklogRemoved,
    WorklogSubmitted,
)
from .vo import TimesheetStatus, WorklogStatus


@dataclass(kw_only=True)
class Worklog(Entity):
    """
    Запись о фактически затраченном времени.
    Может относиться к задаче или тикету.
    """

    timesheet_id: UUID | None = None

    ticket_id: UUID | None = None
    task_id: UUID | None = None

    user_id: UUID  # тот, кто потратил время
    hours_spent: Decimal
    entry_date: date
    description: str | None = None

    status: WorklogStatus

    approved_by: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    def __post_init__(self) -> None:
        # 1. Количество списанных часов не может быть отрицательным
        if self.hours_spent <= 0:
            raise ValueError("Hours spent must be positive")

        # 2. Запись должна принадлежать либо тикету, либо задаче
        if self.ticket_id is None and self.task_id is None:
            raise InvariantViolationError("Worklog must be linked to a ticket or task")

    @classmethod
    def log_time(
            cls,
            user_id: UUID,
            hours_spent: Decimal,
            entry_date: date,
            description: str | None = None,
            ticket_id: UUID | None = None,
            task_id: UUID | None = None,
    ) -> "Worklog":
        """Создание новой записи о потраченном времени (в статусе DRAFT)"""

        worklog = cls(
            user_id=user_id,
            hours_spent=hours_spent,
            entry_date=entry_date,
            ticket_id=ticket_id,
            task_id=task_id,
            description=description,
            status=WorklogStatus.DRAFT,
        )

        # Регистрация доменного события
        worklog.register_event(
            WorklogCreated(
                worklog_id=worklog.id,
                ticket_id=ticket_id,
                task_id=task_id,
                user_id=user_id,
                hours_spent=hours_spent,
                entry_date=entry_date,
            )
        )

        return worklog

    def submit(self) -> None:
        """Отправление записи на согласование"""

        # Отправлять на согласование можно только из черновика
        if self.status != WorklogStatus.DRAFT:
            raise InvalidStateError("Only draft worklogs can be submitted")

        self.status = WorklogStatus.SUBMITTED
        self.updated_at = current_datetime()

        self.register_event(
            WorklogSubmitted(
                worklog_id=self.id,
                ticket_id=self.ticket_id,
                task_id=self.task_id,
                user_id=self.user_id,
                hours_spent=self.hours_spent,
            )
        )

    def approve(self, approved_by: UUID) -> None:
        """
        Согласование записи.
        Вызывает событие для обновления факта потраченных часов в задаче.
        """

        if self.status != WorklogStatus.SUBMITTED:
            raise InvalidStateError("Only submitted worklogs can be approved")

        self.status = WorklogStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = current_datetime()
        self.updated_at = current_datetime()

        self.register_event(
            WorklogApproved(
                worklog_id=self.id,
                ticket_id=self.ticket_id,
                task_id=self.task_id,
                user_id=self.user_id,
                hours_spent=self.hours_spent,
                entry_date=self.entry_date,
                approved_by=approved_by,
            )
        )

    def reject(self, rejected_by: UUID, reason: str) -> None:
        """Отклонение записи с указанием причины"""

        if self.status != WorklogStatus.SUBMITTED:
            raise InvalidStateError("Only submitted entries can be rejected")

        self.status = WorklogStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = current_datetime()

        self.register_event(
            WorklogRejected(
                worklog_id=self.id,
                rejected_by=rejected_by,
                hours_spent=self.hours_spent,
                reason=reason,
            )
        )

    def edit(
            self,
            *,
            hours_spent: Decimal | None = None,
            entry_date: date | None = None,
            description: str | None = None,
    ) -> None:
        """Редактирование записи"""

        if not self.status.is_editable:
            raise InvalidStateError("Worklog in non editable status")

        is_edited = False

        if hours_spent is not None:
            if hours_spent <= 0:
                raise ValueError("Hours spent must be positive")

            self.hours_spent = hours_spent
            is_edited = True

        if entry_date is not None:
            self.entry_date = entry_date
            is_edited = True

        if description is not None and description.strip():
            self.description = description.strip()
            is_edited = True

        if is_edited:
            self.updated_at = current_datetime()

    def assign_to_timesheet(self, timesheet_id: UUID) -> None:
        """Привязать запись к ЛУРВ"""

        if self.timesheet_id is not None:
            raise InvariantViolationError(
                f"Worklog is already assigned to timesheet with ID - '{self.timesheet_id}'"
            )

        self.timesheet_id = timesheet_id
        self.updated_at = current_datetime()

    def remove(self, deleted_by: UUID) -> None:
        """Удаление записи (Soft-delete)"""

        if self.status not in {WorklogStatus.DRAFT, WorklogStatus.REJECTED}:
            raise InvalidStateError("Can only delete DRAFT or REJECTED worklog")

        # Нельзя удалять привязанную к ЛУРВ запись
        if self.timesheet_id is not None:
            raise InvalidStateError("Cannot delete worklog already assigned to timesheet")

        self.deleted_at = current_datetime()

        self.register_event(WorklogRemoved(worklog_id=self.id, deleted_by=deleted_by))


@dataclass(kw_only=True)
class Timesheet(AggregateRoot):
    """
    ЛУРВ - лист учёта рабочего времени.
    Агрегирует фактом потраченных часов.
    Может привязываться к проекту и контрагенту.
    """

    user_id: UUID
    period_start: date
    period_end: date

    name: str

    # Ключевые бизнес срезы (денормализация)
    counterparty_id: UUID | None = None
    project_id: UUID | None = None

    status: TimesheetStatus

    total_hours: Decimal = Decimal(0)
    approved_hours: Decimal = Decimal(0)
    pending_hours: Decimal = Decimal(0)  # часов на согласовании

    worklog_ids: list[UUID] = field(default_factory=list)

    # Аудит действий
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by: UUID | None = None

    def __post_init__(self) -> None:
        # Название листа не может быть пустым
        if not self.name.strip():
            raise ValueError("Timesheet name cannot be empty")

        # Начало периода не может быть больше его конца
        if self.period_start > self.period_end:
            raise InvariantViolationError("Period planned_start cannot be after period planned_end")

        # Количество часов не может быть отрицательным
        if self.total_hours < 0 or self.approved_hours < 0 or self.pending_hours < 0:
            raise InvariantViolationError("The number of hours cannot be negative")

    @property
    def draft_hours(self) -> Decimal:
        """Часов в черновике"""

        return self.total_hours - self.pending_hours - self.approved_hours

    @property
    def worklogs_count(self) -> int:
        """Количество записей в журнале о факте потраченных часов"""

        return len(self.worklog_ids)

    def _recalculate_status(self) -> None:
        """Перерасчёт статуса в зависимости от текущего состояния"""

        # При явном отклонении - авто-обновление запрещено
        if self.status == TimesheetStatus.REJECTED:
            return

        if self.worklogs_count == 0:
            self.status = TimesheetStatus.DRAFT
            return

        if self.pending_hours > 0:
            self.status = TimesheetStatus.SUBMITTED

        # Все часы согласованы - ЛУРВ согласован
        elif self.approved_hours == self.total_hours and self.total_hours > 0:
            self.status = TimesheetStatus.APPROVED

        # Частично согласован
        elif self.approved_hours > 0:
            self.status = TimesheetStatus.PARTIALLY_APPROVED

        else:
            self.status = TimesheetStatus.DRAFT

    @classmethod
    def create(
            cls,
            user_id: UUID,
            period_start: date,
            period_end: date,
            name: str,
            counterparty_id: UUID | None = None,
            project_id: UUID | None = None,
    ) -> "Timesheet":
        """Создание листа учёта рабочего времени за определённый период"""

        return cls(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            name=name,
            counterparty_id=counterparty_id,
            project_id=project_id,
        )

    def add_worklog(
            self,
            worklog_id: UUID,
            hours_spent: Decimal,
            entry_date: date,
            worklog_status: WorklogStatus,
            worklog_user_id: UUID
    ) -> None:
        """Добавление факта потраченных часов в ЛУРВ"""

        if hours_spent <= 0:
            raise ValueError("Cannot add negative number of hours")

        # Нельзя добавить чужой лог в ЛУРВ
        if worklog_user_id != self.user_id:
            raise InvalidStateError(
                f"Cannot add worklog belonging to user '{worklog_user_id}' "
                f"inti timesheet of user '{self.user_id}'"
            )

        if worklog_id in self.worklog_ids:
            return

        # Дата лога должна попадать в диапазон ЛУРВ
        if not (self.period_start <= entry_date <= self.period_end):
            raise InvariantViolationError("Worklog date is out of timesheet period")

        self.worklog_ids.append(worklog_id)
        self.total_hours += hours_spent

        # Учитываем текущий статус записи
        if worklog_status == WorklogStatus.SUBMITTED:
            self.pending_hours += hours_spent
        elif worklog_status == WorklogStatus.APPROVED:
            self.approved_hours += hours_spent

        self._recalculate_status()

        self.updated_at = current_datetime()

    def remove_worklog(
            self, worklog_id: UUID, hours_spent: Decimal, worklog_status: WorklogStatus
    ) -> None:
        """Удаление записи о потраченных часах из ЛУРВ"""

        if hours_spent <= 0:
            raise ValueError("Cannot remove negative number of hours")

        if worklog_id not in self.worklog_ids:
            return

        self.worklog_ids.remove(worklog_id)
        self.total_hours -= hours_spent

        # Учитываем текущий статус записи
        if worklog_status == WorklogStatus.SUBMITTED:
            self.pending_hours -= hours_spent
        elif worklog_status == WorklogStatus.APPROVED:
            self.approved_hours -= hours_spent

        self._recalculate_status()

        self.updated_at = current_datetime()

    def submit(self) -> None:
        """Отправить ЛУРВ на согласование"""

        if self.status not in {
            TimesheetStatus.DRAFT, TimesheetStatus.REJECTED, TimesheetStatus.PARTIALLY_APPROVED
        }:
            raise InvalidStateError("Only DRAFT or REJECTED timesheet can be submitted")

        if not self.worklog_ids:
            raise InvariantViolationError(
                "Cannot submit empty timesheet. Need at least one worklog!"
            )

        self.status = TimesheetStatus.SUBMITTED
        self.submitted_at = current_datetime()

        self.register_event(
            TimesheetSubmitted(
                timesheet_id=self.id,
                user_id=self.user_id,
                total_hours=self.total_hours,
                submitted_at=self.submitted_at,
            )
        )

    def approve(self, approved_by: UUID) -> None:
        """Согласовать ЛУРВ"""

        if self.status != TimesheetStatus.SUBMITTED:
            raise InvalidStateError("Only SUBMITTED timesheet can be approved")

        self.status = TimesheetStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = current_datetime()
        self.updated_at = current_datetime()

        self.register_event(
            TimesheetApproved(
                timesheet_id=self.id,
                approved_by=approved_by,
                approved_at=self.approved_at,
                total_hours=self.total_hours,
            )
        )

    def reject(self, rejected_by: UUID, reason: str) -> None:
        """Отклонение всего ЛУРВ"""

        if self.status != TimesheetStatus.SUBMITTED:
            raise InvalidStateError("Only SUBMITTED timesheet can be rejected")

        if not reason.strip():
            raise ValueError("Rejection reason cannot be empty")

        self.status = TimesheetStatus.REJECTED
        self.updated_at = current_datetime()

        self.register_event(
            TimesheetRejected(
                timesheet_id=self.id,
                rejected_by=rejected_by,
                reason=reason,
            )
        )
