from typing import Annotated

from fastapi import Depends

from ..crm.dependencies import CounterpartyRepoDep
from ..projects.dependencies import ProjectRepoDep
from ..shared.dependencies import EventPublisherDep, SessionDep
from ..tasks.dependencies import TaskRepoDep
from ..tickets.dependencies import TicketRepoDep
from .domain.repos import TimesheetRepository, WorklogRepository
from .infra.repos import SqlTimesheetRepository, SqlWorklogRepository
from .services import TimesheetService, WorklogService


def get_worklog_repo(session: SessionDep) -> SqlWorklogRepository:
    return SqlWorklogRepository(session)


def get_timesheet_repo(session: SessionDep) -> SqlTimesheetRepository:
    return SqlTimesheetRepository(session)


WorklogRepoDep = Annotated[WorklogRepository, Depends(get_worklog_repo)]
TimesheetRepoDep = Annotated[TimesheetRepository, Depends(get_timesheet_repo)]


def get_worklog_service(
        session: SessionDep,
        worklog_repo: WorklogRepoDep,
        task_repo: TaskRepoDep,
        ticket_repo: TicketRepoDep,
        event_publisher: EventPublisherDep,
) -> WorklogService:
    return WorklogService(
        session=session,
        worklog_repo=worklog_repo,
        task_repo=task_repo,
        ticket_repo=ticket_repo,
        event_publisher=event_publisher,
    )


def get_timesheet_service(
        session: SessionDep,
        timesheet_repo: TimesheetRepoDep,
        worklog_repo: WorklogRepoDep,
        counterparty_repo: CounterpartyRepoDep,
        project_repo: ProjectRepoDep,
        event_publisher: EventPublisherDep,
) -> TimesheetService:
    return TimesheetService(
        session=session,
        timesheet_repo=timesheet_repo,
        worklog_repo=worklog_repo,
        counterparty_repo=counterparty_repo,
        project_repo=project_repo,
        event_publisher=event_publisher,
    )


WorklogServiceDep = Annotated[WorklogService, Depends(get_worklog_service)]
TimesheetServiceDep = Annotated[TimesheetService, Depends(get_timesheet_service)]
