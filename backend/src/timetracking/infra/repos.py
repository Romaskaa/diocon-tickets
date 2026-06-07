from typing import Any

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ...tasks.infra.models import TaskOrm
from ...tickets.infra.models import TicketOrm
from ..domain.entities import Timesheet, Worklog
from ..domain.vo import WorklogStatus
from .models import TimesheetOrm, WorklogOrm


class WorklogMapper(ModelMapper[Worklog, WorklogOrm]):

    @staticmethod
    def to_entity(model: WorklogOrm) -> Worklog:
        return Worklog(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            timesheet_id=model.timesheet_id,
            ticket_id=model.ticket_id,
            task_id=model.task_id,
            user_id=model.user_id,
            hours_spent=model.hours_spent,
            entry_date=model.entry_date,
            description=model.description,
            status=model.status,
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            rejection_reason=model.rejection_reason,
        )

    @staticmethod
    def from_entity(entity: Worklog) -> WorklogOrm:
        return WorklogOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            timesheet_id=entity.timesheet_id,
            ticket_id=entity.ticket_id,
            task_id=entity.task_id,
            user_id=entity.user_id,
            hours_spent=entity.hours_spent,
            entry_date=entity.entry_date,
            description=entity.description,
            status=entity.status,
            approved_by=entity.approved_by,
            approved_at=entity.approved_at,
            rejection_reason=entity.rejection_reason,
        )

    @staticmethod
    def form_entity_to_upsert_data(entity: Worklog) -> dict[str, Any]:
        return {
            "updated_at": entity.updated_at,
            "deleted_at": entity.deleted_at,
            "timesheet_id": entity.timesheet_id,
            "ticket_id": entity.ticket_id,
            "task_id": entity.task_id,
            "user_id": entity.user_id,
            "hours_spent": entity.hours_spent,
            "entry_date": entity.entry_date,
            "description": entity.description,
            "status": entity.status,
            "approved_by": entity.approved_by,
            "approved_at": entity.approved_at,
            "rejection_reason": entity.rejection_reason,
        }


class SqlWorklogRepository(SqlAlchemyRepository[Worklog, WorklogOrm]):
    model = WorklogOrm
    model_mapper = WorklogMapper

    async def bulk_upsert(self, worklogs: list[Worklog]) -> None:
        if not worklogs:
            return

        stmt = pg_insert(self.model)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "updated_at": stmt.excluded.updated_at,
                "deleted_at": stmt.excluded.deleted_at,
                "timesheet_id": stmt.excluded.timesheet_id,
                "ticket_id": stmt.excluded.ticket_id,
                "task_id": stmt.excluded.task_id,
                "user_id": stmt.excluded.user_id,
                "hours_spent": stmt.excluded.hours_spent,
                "entry_date": stmt.excluded.entry_date,
                "description": stmt.excluded.description,
                "status": stmt.excluded.status,
                "approved_by": stmt.excluded.approved_by,
                "approved_at": stmt.excluded.approved_at,
                "rejection_reason": stmt.excluded.rejection_reason,
            }
        )

        data_to_upsert = [
            self.model_mapper.form_entity_to_upsert_data(worklog) for worklog in worklogs
        ]
        await self.session.execute(stmt, data_to_upsert)
        self.session.expire_all()

    async def get_unassigned_in_period(
            self,
            user_id: UUID,
            date_from: date,
            date_to: date,
            counterparty_id: UUID | None = None,
            project_id: UUID | None = None,
            statuses: list[WorklogStatus] | None = None,
    ) -> list[Worklog]:
        stmt = select(self.model).where(
            (self.model.user_id == user_id) &
            (self.model.entry_date.between(date_from, date_to)) &
            (self.model.timesheet_id.is_(None))
        )

        # Фильтрация по статусам
        if statuses is not None and statuses:
            stmt = stmt.where(self.model.status.in_(statuses))

        # JOIN для фильтрации по контрагенту и проекту
        if counterparty_id is not None or project_id is not None:
            stmt = stmt.outerjoin(TicketOrm, self.model.ticket_id == TicketOrm.id)

        if project_id is not None:
            stmt = stmt.outerjoin(TaskOrm, self.model.task_id == TaskOrm.id)

        if counterparty_id is not None:
            stmt = stmt.where(TicketOrm.counterparty_id == counterparty_id)

        if project_id is not None:
            stmt = stmt.where(
                (TicketOrm.project_id == project_id) |
                (TaskOrm.project_id == project_id)
            )

        # Сортировка от старой дате к новой
        stmt = stmt.order_by(self.model.entry_date.asc())

        results = await self.session.execute(stmt)

        return [self.model_mapper.to_entity(model) for model in results.scalars().all()]


class TimesheetMapper(ModelMapper[Timesheet, TimesheetOrm]):

    @staticmethod
    def to_entity(model: TimesheetOrm) -> Timesheet:
        return Timesheet(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            user_id=model.user_id,
            period_start=model.period_start,
            period_end=model.period_end,
            name=model.name,
            counterparty_id=model.counterparty_id,
            project_id=model.project_id,
            status=model.status,
            total_hours=model.total_hours,
            approved_hours=model.approved_hours,
            pending_hours=model.pending_hours,
            worklog_ids=model.worklog_ids,
            submitted_at=model.submitted_at,
            approved_at=model.approved_at,
            approved_by=model.approved_by,
        )

    @staticmethod
    def from_entity(entity: Timesheet) -> TimesheetOrm:
        return TimesheetOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            user_id=entity.user_id,
            period_start=entity.period_start,
            period_end=entity.period_end,
            name=entity.name,
            counterparty_id=entity.counterparty_id,
            project_id=entity.project_id,
            status=entity.status,
            total_hours=entity.total_hours,
            approved_hours=entity.approved_hours,
            pending_hours=entity.pending_hours,
            worklog_ids=entity.worklog_ids,
            submitted_at=entity.submitted_at,
            approved_at=entity.approved_at,
            approved_by=entity.approved_by,
        )


class SqlTimesheetRepository(SqlAlchemyRepository[Timesheet, TimesheetOrm]):
    model = TimesheetOrm
    model_mapper = TimesheetMapper
