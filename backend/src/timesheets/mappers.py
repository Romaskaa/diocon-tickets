from .domain.entities import Timesheet, Worklog
from .schemas import TimesheetResponse, WorklogResponse


def map_worklog_to_response(worklog: Worklog) -> WorklogResponse:
    return WorklogResponse(
        id=worklog.id,
        created_at=worklog.created_at,
        updated_at=worklog.updated_at,
        timesheet_id=worklog.timesheet_id,
        ticket_id=worklog.ticket_id,
        task_id=worklog.task_id,
        user_id=worklog.user_id,
        hours_spent=worklog.hours_spent,
        entry_date=worklog.entry_date,
        description=worklog.description,
        status=worklog.status,
        approved_by=worklog.approved_by,
        approved_at=worklog.approved_at,
        rejection_reason=worklog.rejection_reason,
    )


def map_timesheet_to_response(timesheet: Timesheet) -> TimesheetResponse:
    return TimesheetResponse(
        id=timesheet.id,
        created_at=timesheet.created_at,
        updated_at=timesheet.updated_at,
        user_id=timesheet.user_id,
        period_start=timesheet.period_start,
        period_end=timesheet.period_end,
        name=timesheet.name,
        counterparty_id=timesheet.counterparty_id,
        project_id=timesheet.project_id,
        status=timesheet.status,
        total_hours=timesheet.total_hours,
        approved_hours=timesheet.approved_hours,
        pending_hours=timesheet.pending_hours,
        draft_hours=timesheet.draft_hours,
        worklogs_count=timesheet.worklogs_count,
        worklog_ids=timesheet.worklog_ids,
        submitted_at=timesheet.submitted_at,
        approved_at=timesheet.approved_at,
        approved_by=timesheet.approved_by,
    )
