from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.activity_logs.recorder import ActivityLogRecorder
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.repos import UserRepository
from src.iam.schemas import CurrentUser
from src.projects.domain.repos import ProjectRepository
from src.projects.domain.services import ProjectAccessService
from src.shared.domain.events import EventPublisher
from src.shared.domain.exceptions import InvalidStateError, NotFoundError

from ...tasks.domain.acl import (
    can_archive_task,
    can_assign_task,
    can_create_task,
    can_edit_task,
    can_move_status,
    can_request_review,
    can_review_task,
)
from ...tasks.domain.entities import Task
from ...tasks.domain.repos import TaskRepository
from ...tasks.domain.vo import TaskNumber, TaskStatus
from ...tasks.mappers import map_task_to_response
from ...tasks.schemas import TaskCreate, TaskEdit, TaskResponse, TaskReview
from ...tickets.domain.entities import Ticket
from ...tickets.domain.repos import TicketRepository
from ...tickets.domain.vo import Tag


class TaskService:
    def __init__(
            self,
            session: AsyncSession,
            task_repo: TaskRepository,
            ticket_repo: TicketRepository,
            user_repo: UserRepository,
            project_repo: ProjectRepository,
            project_access_service: ProjectAccessService,
            activity_log_recorder: ActivityLogRecorder,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.task_repo = task_repo
        self.ticket_repo = ticket_repo
        self.user_repo = user_repo
        self.project_repo = project_repo
        self.project_access_service = project_access_service
        self.activity_log_recorder = activity_log_recorder
        self.event_publisher = event_publisher

    @staticmethod
    def _resolve_project_id(
            data: TaskCreate, ticket: Ticket | None = None
    ) -> UUID | None:
        """
        Определение правильного ID проекта для привязи к задаче
        """

        project_id = data.project_id

        # Если указан тикет - проверка на его существование + подтягивание проекта
        if ticket is not None and ticket.project_id is not None:

            # Указанный проект и проект тикета должны совпадать
            if project_id is not None and project_id != ticket.project_id:
                raise InvalidStateError("Project mismatch with ticket")

            project_id = ticket.project_id

        return project_id

    async def create(self, data: TaskCreate, current_user: CurrentUser) -> TaskResponse:
        """Создание задачи"""

        # 1. Проверка прав на создание задачи
        permission = can_create_task(current_user.role)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 2. Получение тикета если он указан для создания задачи
        ticket = None
        if data.ticket_id is not None:
            ticket = await self.ticket_repo.read(data.ticket_id)
            if ticket is None:
                raise NotFoundError(f"Ticket with ID {data.ticket_id} not found")

        # 3. Разрешение проекта
        project_id = self._resolve_project_id(data, ticket)

        # 4. Проверка проекта на существование + авторизация
        project_key = None

        if project_id is not None:
            project = await self.project_repo.read(project_id)
            if project is None:
                raise NotFoundError(f"Project with ID {project_id} not found")

            project_key = project.key

            # 4.1. Проверка прав на создание проекта
            permission = await self.project_access_service.can_create_task(
                project_id=project_id,
                user_id=current_user.user_id,
                user_role=current_user.role
            )
            if not permission.allowed:
                raise PermissionDeniedError(permission.reason)

        # 5. Создание задачи с уникальным номером
        sequence = await self.task_repo.get_next_sequence(
            ticket_id=None if ticket is None else ticket.id, project_id=project_id
        )
        task_number = TaskNumber.create(
            ticket_number=None if ticket is None else ticket.number,
            project_key=project_key,
            sequence=sequence,
        )

        task = Task.create(
            number=task_number,
            title=data.title,
            description=data.description,
            priority=data.priority,
            due_date=data.due_date,
            estimated_hours=data.estimated_hours,
            project_id=project_id,
            ticket_id=data.ticket_id,
            created_by=current_user.user_id,
            tags=[Tag(name=tag.name, color=tag.color) for tag in data.tags]
        )
        if data.mark_as_todo:
            task.change_status(new_status=TaskStatus.TODO, changed_by=current_user.user_id)

        await self.task_repo.create(task)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in task.collect_events():
            await self.event_publisher.publish(event)

        return map_task_to_response(task)

    async def move_to(
            self, task_id: UUID, new_status: TaskStatus, current_user: CurrentUser
    ) -> TaskResponse:
        """Изменение статуса задачи"""

        # 1. Получение и проверка задачи на существование
        task = await self.task_repo.read(task_id)
        if task is None:
            raise NotFoundError(f"Task with ID {task_id} not found")

        # 2. Проверка прав на изменение статуса задачи
        permission = can_move_status(
            task=task,
            new_status=new_status,
            user_id=current_user.user_id,
            user_role=current_user.role
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Изменение статуса задачи и обновление сущности
        task.change_status(new_status=new_status, changed_by=current_user.user_id)
        await self.task_repo.update(task)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in task.collect_events():
            await self.event_publisher.publish(event)

        return map_task_to_response(task)

    async def edit(self, task_id: UUID, data: TaskEdit, current_user: CurrentUser) -> TaskResponse:
        """Редактирование задачи"""

        # 1. Получение задачи и проверка её на существование
        task = await self.task_repo.read(task_id)
        if task is None or task.is_deleted:
            raise NotFoundError(f"Task with ID {task_id} not found")

        # 2. Проверка прав на редактирование задачи
        permission = can_edit_task(
            task=task, user_id=current_user.user_id, user_role=current_user.role
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Редактирование задачи и обновление сущности
        task.edit(
            title=data.title,
            description=data.description,
            priority=data.priority,
            story_points=data.story_points,
            estimated_hours=data.estimated_hours,
            due_date=data.due_date,
        )
        await self.task_repo.update(task)
        await self.session.commit()

        # 4. публикация доменных событий
        for event in task.collect_events():
            await self.event_publisher.publish(event)

        return map_task_to_response(task)

    async def assign_to(
            self, task_id: UUID, assignee_id: UUID, current_user: CurrentUser
    ) -> TaskResponse:
        """Назначить исполнителя на задачу"""

        # 1. Получение и проверка задачи на существование
        task = await self.task_repo.read(task_id)
        if task is None:
            raise NotFoundError(f"Task with ID {task_id} not found")

        # 2. Получение исполнителя и проверка его на существование
        assignee = await self.user_repo.read(assignee_id)
        if assignee is None or assignee.is_deleted:
            raise NotFoundError(f"User with ID {assignee_id} not found")

        # 3. Поверка прав на назначение исполнителя
        permission = can_assign_task(
            task=task,
            assignee_role=assignee.role,
            user_id=current_user.user_id,
            user_role=current_user.role
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 4. Назначение исполнителя и обновление сущности
        task.assign_to(assignee_id=assignee_id, assigned_by=current_user.user_id)
        await self.task_repo.update(task)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in task.collect_events():
            await self.event_publisher.publish(event)

        return map_task_to_response(task)

    async def request_review(
            self, task_id: UUID, reviewer_id: UUID, current_user: CurrentUser
    ) -> TaskResponse:
        """Запросить ревью задачи"""

        # 1. Получение и проверка задачи на существование
        task = await self.task_repo.read(task_id)
        if task is None:
            raise NotFoundError(f"Task with ID {task_id} not found")

        # 2. Получение и проверка га существование указанного проверяющего задачи
        reviewer = await self.user_repo.read(reviewer_id)
        if reviewer is None or reviewer.is_deleted:
            raise NotFoundError(f"Reviewer with ID {reviewer_id} not found")

        # 2. Проверка прав на запрос ревью задачи
        permission = can_request_review(
            task=task,
            reviewer_role=reviewer.role,
            user_id=current_user.user_id,
            user_role=current_user.role,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Запрос ревью и обновление состояния задачи
        task.request_review(reviewer_id=reviewer_id, requested_by=current_user.user_id)
        await self.task_repo.update(task)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in task.collect_events():
            await self.event_publisher.publish(event)

        return map_task_to_response(task)

    async def review(
            self, task_id: UUID, data: TaskReview, current_user: CurrentUser
    ) -> TaskResponse:
        """Провести ревью задачи"""

        # 1. Получение и проверка задачи на существование
        task = await self.task_repo.read(task_id)
        if task is None:
            raise NotFoundError(f"Task with ID {task_id} not found")

        # 2. Проверка прав на ревью задачи
        permission = can_review_task(
            task=task, user_id=current_user.user_id, user_role=current_user.role
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Перевод задачи к новому статусу и обновление сущности
        if data.action == "approve":
            task.approve_review(approved_by=current_user.user_id)
        if data.action == "reject":
            task.reject_review(rejected_by=current_user.user_id)

        await self.task_repo.update(task)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in task.collect_events():
            await self.event_publisher.publish(event)

        return map_task_to_response(task)

    async def archive(self, task_id: UUID, current_user: CurrentUser) -> TaskResponse:
        """Архивирование задачи"""

        # 1. Получение и проверка на существование
        task = await self.task_repo.read(task_id)
        if task is None:
            raise NotFoundError(f"Task with ID {task_id} not found")

        # 2. Проверка прав на архивирование
        permission = can_archive_task(
            task=task, user_id=current_user.user_id, user_role=current_user.role
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Архивация и обновление сущности
        task.archive(archived_by=current_user.user_id)
        await self.task_repo.update(task)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in task.collect_events():
            await self.event_publisher.publish(event)

        return map_task_to_response(task)

    async def add_actual_hours(self, task_id: UUID, hours: Decimal) -> None:
        """Добавление фактических трудозатрат по задаче"""

        # 1. Получение и проверка на существование
        task = await self.task_repo.read(task_id)
        if task is None:
            raise NotFoundError(f"Task with ID {task_id} not found")

        # 2. Добавление часов + обновление состояния
        task.add_actual_hours(hours)
        await self.task_repo.update(task)
        await self.session.commit()
