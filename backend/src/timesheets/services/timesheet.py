from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...crm.domain.repo import CounterpartyRepository
from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.schemas import CurrentUser
from ...projects.domain.repos import ProjectRepository
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import NotFoundError
from ..domain.authz import can_approve_timesheet, can_create_timesheet, can_submit_timesheet
from ..domain.entities import Timesheet
from ..domain.repos import TimesheetRepository, WorklogRepository
from ..domain.services import (
    approve_worklogs_in_timesheet,
    assign_worklogs_to_timesheets,
    submit_worklogs_in_timesheet,
)
from ..mappers import map_timesheet_to_response
from ..schemas import TimesheetCreate, TimesheetResponse


class TimesheetService:
    def __init__(
            self,
            session: AsyncSession,
            timesheet_repo: TimesheetRepository,
            worklog_repo: WorklogRepository,
            counterparty_repo: CounterpartyRepository,
            project_repo: ProjectRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.timesheet_repo = timesheet_repo
        self.worklog_repo = worklog_repo
        self.counterparty_repo = counterparty_repo
        self.project_repo = project_repo
        self.event_publisher = event_publisher

    async def _resolve_counterparty_id(
            self, counterparty_id: UUID | None, project_id: UUID | None
    ) -> UUID | None:
        """Определение ID контрагента для создания ЛУРВ"""

        # 1. Проверка контрагента на существование
        if counterparty_id is not None:
            counterparty = await self.counterparty_repo.read(counterparty_id)
            if counterparty is None:
                raise NotFoundError(f"Counterparty with ID {counterparty_id} not found")

        # 2. проверка проекта на существование + подтягивание ID контрагента из проекта
        if project_id is not None:
            project = await self.project_repo.read(project_id)
            if project is None:
                raise NotFoundError(f"Project with ID {project_id} not found")

            # 2.1. Подтягиваем контрагента из проекта
            if project.counterparty_id is not None:
                counterparty_id = project.counterparty_id

        return counterparty_id

    async def create(self, data: TimesheetCreate, current_user: CurrentUser) -> TimesheetResponse:
        """Формирование нового ЛУРВ"""

        # 1. Поверка прав на создание
        permission = can_create_timesheet(current_user.role)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 2. Определение контрагента
        counterparty_id = await self._resolve_counterparty_id(
            counterparty_id=data.counterparty_id, project_id=data.project_id
        )

        # 3. Создание и сохранение агрегата
        timesheet = Timesheet.create(
            user_id=current_user.user_id,
            period_start=data.period_start,
            period_end=data.period_end,
            name=data.name,
            counterparty_id=counterparty_id,
            project_id=data.project_id,
        )

        # 3.1. Авто-добавление логов
        if data.auto_add_worklogs:
            worklogs = await self.worklog_repo.get_unassigned_in_period(
                user_id=current_user.user_id,
                date_from=data.period_start,
                date_to=data.period_end,
                counterparty_id=counterparty_id,
                project_id=data.project_id,
            )
            assign_worklogs_to_timesheets(timesheet, worklogs)

            await self.worklog_repo.bulk_upsert(worklogs)

        await self.timesheet_repo.create(timesheet)
        await self.session.commit()

        # 4. Публикация доенных событий
        for event in timesheet.collect_events():
            await self.event_publisher.publish(event)

        return map_timesheet_to_response(timesheet)

    async def submit(self, timesheet_id: UUID, current_user: CurrentUser) -> TimesheetResponse:
        """Отправка ЛУРВ на согласование"""

        # 1. Загрузка ЛУРВ
        timesheet = await self.timesheet_repo.read(timesheet_id)
        if timesheet is None:
            raise NotFoundError(f"Timesheet with ID {timesheet_id} not found")

        # 2. Проверка прав
        permission = can_submit_timesheet(
            timesheet=timesheet,
            user_id=current_user.user_id,
            user_role=current_user.role,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Получение рабочего журнала
        worklogs = await self.worklog_repo.get_by_ids(timesheet.worklog_ids)

        # 4. Отправка на согласование + обновление состояния
        submit_worklogs_in_timesheet(timesheet, worklogs)

        await self.timesheet_repo.upsert(timesheet)
        await self.worklog_repo.bulk_upsert(worklogs)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in timesheet.collect_events():
            await self.event_publisher.publish(event)

        return map_timesheet_to_response(timesheet)

    async def approve(self, timesheet_id: UUID, current_user: CurrentUser) -> TimesheetResponse:
        """Согласовать ЛУРВ"""

        # 1. Загрузка ЛУРВ
        timesheet = await self.timesheet_repo.read(timesheet_id)
        if timesheet is None:
            raise NotFoundError(f"Timesheet with ID {timesheet_id} not found")

        # 2. Проверка прав
        permission = can_approve_timesheet(current_user.role)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Получение журнала выполненных работ
        worklogs = await self.worklog_repo.get_by_ids(timesheet.worklog_ids)

        # 4. Согласование и обновление состояния
        approve_worklogs_in_timesheet(timesheet, worklogs, approved_by=current_user.user_id)

        await self.timesheet_repo.upsert(timesheet)
        await self.worklog_repo.bulk_upsert(worklogs)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in timesheet.collect_events():
            await self.event_publisher.publish(event)

        for worklog in worklogs:
            for event in worklog.collect_events():
                await self.event_publisher.publish(event)

        return map_timesheet_to_response(timesheet)
