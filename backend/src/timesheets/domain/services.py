from uuid import UUID

from ...shared.domain.exceptions import InvariantViolationError
from ...tasks.domain.entities import Task
from .entities import Timesheet, Worklog
from .vo import WorklogStatus


def ensure_task_belongs_to_ticket(task: Task | None, ticket_id: UUID | None) -> None:
    """Обеспечивает принадлежность задачи указанному тикету"""

    if task is not None and ticket_id is not None and task.ticket_id != ticket_id:
        raise InvariantViolationError(
            "Task does not belong to ticket", details={"task_id": task.id, "ticket_id": ticket_id}
        )


def assign_worklogs_to_timesheets(timesheet: Timesheet, worklogs: list[Worklog]) -> None:
    """Массовое добавление записей о потраченном времени в ЛУРВ"""

    for worklog in worklogs:
        worklog.assign_to_timesheet(timesheet.id)
        timesheet.add_worklog(
            worklog_id=worklog.id,
            hours_spent=worklog.hours_spent,
            entry_date=worklog.entry_date,
            worklog_status=worklog.status,
            worklog_user_id=worklog.user_id,
        )


def submit_worklogs_in_timesheet(timesheet: Timesheet, worklogs: list[Worklog]) -> None:
    """Отправка журнала работ на согласование в рамках ЛУРВ"""

    worklog_ids = {worklog.id for worklog in worklogs}
    if worklog_ids != set(timesheet.worklog_ids):
        raise InvariantViolationError("The provided worklogs do not match the timesheet items")

    for worklog in worklogs:
        worklog.submit()

    timesheet.submit()


def approve_worklogs_in_timesheet(
        timesheet: Timesheet, worklogs: list[Worklog], approved_by: UUID
) -> None:
    """Согласовать все часы работ в рамках ЛУРВ"""

    worklog_ids = {worklog.id for worklog in worklogs}
    if worklog_ids != set(timesheet.worklog_ids):
        raise InvariantViolationError("The provided worklogs do not match the timesheet items")

    for worklog in worklogs:
        worklog.approve(approved_by)

    timesheet.approve(approved_by)


def reject_worklogs_in_timesheet(
        timesheet: Timesheet, worklogs: list[Worklog], rejected_by: UUID, reason: str
) -> None:
    """Отклонение ЛУРВ и всего журнала работ"""

    worklog_ids = {worklog.id for worklog in worklogs}
    if worklog_ids != set(timesheet.worklog_ids):
        raise InvariantViolationError("The provided worklogs do not match the timesheet items")

    for worklog in worklogs:
        if worklog.status == WorklogStatus.SUBMITTED:
            worklog.reject(rejected_by, reason)

        # Если хотя бы одна запись согласована - нельзя отклонить весь ЛУРВ
        elif worklog.status == WorklogStatus.APPROVED:
            raise InvariantViolationError(
                f"Cannot reject timesheet: worklog {worklog.id} is already approved"
            )

    timesheet.reject(rejected_by, reason)
