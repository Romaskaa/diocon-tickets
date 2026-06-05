from typing import Annotated

from fastapi import Depends

from ..shared.dependencies import EventPublisherDep, SessionDep
from ..tasks.dependencies import TaskRepoDep
from ..tickets.dependencies import TicketRepoDep
from .domain.repos import WorklogRepository
from .infra.repos import SqlWorklogRepository
from .services import WorklogService


def get_worklog_repo(session: SessionDep) -> SqlWorklogRepository:
    return SqlWorklogRepository(session)


WorklogRepoDep = Annotated[WorklogRepository, Depends(get_worklog_repo)]


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


WorklogServiceDep = Annotated[WorklogService, Depends(get_worklog_service)]
