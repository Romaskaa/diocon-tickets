from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.schemas import CurrentUser
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import NotFoundError
from ...tasks.domain.entities import Task
from ...tasks.domain.repos import TaskRepository
from ...tickets.domain.entities import Ticket
from ...tickets.domain.repos import TicketRepository
from ...timesheets.domain.authz import can_edit_worklog, can_log_time
from ...timesheets.domain.entities import Worklog
from ...timesheets.domain.repos import WorklogRepository
from ...timesheets.domain.services import ensure_task_belongs_to_ticket
from ...timesheets.mappers import map_worklog_to_response
from ...timesheets.schemas import WorklogCreate, WorklogEdit, WorklogResponse


@dataclass(frozen=True)
class WorklogCreationContext:
    """Контекст для создания лога о потраченном времени"""

    task: Task | None = None
    ticket: Ticket | None = None
    task_id: UUID | None = None
    ticket_id: UUID | None = None


class WorklogService:
    def __init__(
            self,
            session: AsyncSession,
            worklog_repo: WorklogRepository,
            task_repo: TaskRepository,
            ticket_repo: TicketRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.worklog_repo = worklog_repo
        self.task_repo = task_repo
        self.ticket_repo = ticket_repo
        self.event_publisher = event_publisher

    async def _resolve_creation_context(
            self, task_id: UUID | None, ticket_id: UUID | None
    ) -> WorklogCreationContext:
        """
        Определение контекста создание записи журнала.
        Метод выполняет загрузку задачи и тикета из хранилища
        и применяет бизнес-правила связывания задачи и тикета:
         1. Если передан только task_id, автоматически определяет ticket_id из задачи.
         2. Если переданы оба ID, проверяет сквозной инвариант их совместимости.
        """

        if task_id is None and ticket_id is None:
            raise ValueError("Ticket or task must be specified for worklog")

        task, ticket = None, None

        # 1. Загрузка задачи + проверка на существование
        if task_id is not None:
            task = await self.task_repo.read(task_id)
            if task is None:
                raise NotFoundError(f"Task with ID {task_id} not found")

            # 1.1. Если тикет привязан к задаче, то подтягиваем его ID
            if ticket_id is None:
                ticket_id = task.ticket_id

            # 1.2. Проверка согласованности задачи и тикета
            ensure_task_belongs_to_ticket(task, ticket_id)

        # 2. если указан тикет - проверка его существования
        if ticket_id is not None:
            ticket = await self.ticket_repo.read(ticket_id)
            if ticket is None:
                raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        return WorklogCreationContext(task=task, ticket=ticket, ticket_id=ticket_id)

    async def log_time(self, data: WorklogCreate, current_user: CurrentUser) -> WorklogResponse:
        """Запись факта потраченных часов в журнал"""

        # 1. Определение контекста для создания записи
        context = await self._resolve_creation_context(
            task_id=data.task_id, ticket_id=data.ticket_id
        )

        # 2. Авторизация и проверка прав
        permission = can_log_time(
            ticket=context.ticket,
            task=context.task,
            user_id=current_user.user_id,
            user_role=current_user.role,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Создание и сохранение сущности
        worklog = Worklog.log_time(
            user_id=current_user.user_id,
            hours_spent=data.hours_spent,
            entry_date=data.entry_date,
            description=data.description,
            ticket_id=context.ticket_id,
            task_id=context.task_id,
        )
        await self.worklog_repo.create(worklog)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in worklog.collect_events():
            await self.event_publisher.publish(event)

        return map_worklog_to_response(worklog)

    async def edit(
            self, worklog_id: UUID, data: WorklogEdit, current_user: CurrentUser
    ) -> WorklogResponse:
        """Редактирование записи журнала о потраченном времени"""

        # 1. Загрузка лога + проверка на существование
        worklog = await self.worklog_repo.read(worklog_id)
        if worklog is None:
            raise NotFoundError(f"Worklog with ID {worklog_id} not found")

        # 2. Проверка прав
        permission = can_edit_worklog(
            worklog=worklog, user_id=current_user.user_id, user_role=current_user.role
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Редактирование и обновление сущности
        worklog.edit(
            hours_spent=data.hours_spent,
            entry_date=data.entry_date,
            description=data.description,
        )
        await self.worklog_repo.upsert(worklog)
        await self.session.commit()

        return map_worklog_to_response(worklog)
