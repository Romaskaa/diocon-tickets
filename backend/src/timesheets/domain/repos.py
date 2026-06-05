
from datetime import date
from uuid import UUID

from ...shared.domain.repo import Repository
from .entities import Timesheet, Worklog
from .vo import WorklogStatus


class WorklogRepository(Repository[Worklog]):

    async def bulk_upsert(self, worklogs: list[Worklog]) -> None: ...

    async def get_unassigned_in_period(
            self,
            user_id: UUID,
            date_from: date,
            date_to: date,
            counterparty_id: UUID | None = None,
            project_id: UUID | None = None,
            statuses: list[WorklogStatus] | None = None,
    ) -> list[Worklog]: ...

    async def get_by_task(self, task_id: UUID) -> list[Worklog]: ...

    async def get_by_ticket(self, ticket_id: UUID) -> list[Worklog]: ...


class TimesheetRepository(Repository[Timesheet]):
    ...
