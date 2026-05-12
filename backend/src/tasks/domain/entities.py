from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from ...shared.domain.entities import Entity
from ...shared.domain.exceptions import InvalidStateError
from ...shared.utils.time import current_datetime
from ...tickets.domain.vo import TicketPriority
from .constants import ALLOWED_TRANSITIONS
from .events import TaskCreated, TaskStatusMoved
from .vo import StoryPoints, TaskStatus


@dataclass(kw_only=True)
class Team(Entity):
    """

    """

    name: str
    description: str | None = None
    lead_id: UUID
    is_active: bool = True


@dataclass(kw_only=True)
class Task(Entity):
    """
    Задача для специалиста.
    Используется для детализации работ, например по большому тикету.
    """

    ticket_id: UUID | None = None
    title: str
    description: str | None = None
    status: TaskStatus
    priority: TicketPriority
    story_points: StoryPoints | None = None

    # Исполнитель и ответственный
    assignee_id: UUID | None = None
    reviewer_id: UUID | None = None

    # Трудозатраты (оценка и факт)
    estimated_hours: Decimal | None = None
    actual_hours: Decimal = Decimal(0)

    # Сроки
    due_date: date | None = None  # срок выполнения
    started_at: datetime | None = None
    completed_at: datetime | None = None

    created_by: UUID

    @classmethod
    def create(
            cls,
            title: str,
            created_by: UUID,
            description: str | None = None,
            priority: TicketPriority = TicketPriority.MEDIUM,
            ticket_id: UUID | None = None,
            due_date: date | None = None,
            estimated_hours: Decimal | None = None,
    ) -> "Task":
        """Создание задачи"""

        task_id = uuid4()
        task = cls(
            id=task_id,
            ticket_id=ticket_id,
            title=title,
            description=description,
            status=TaskStatus.BACKLOG,
            priority=priority,
            due_date=due_date,
            estimated_hours=estimated_hours,
            created_by=created_by,
        )

        # Регистрация доменного объекта
        task.register_event(
            TaskCreated(
                task_id=task_id,
                ticket_id=ticket_id,
                title=title,
                created_by=created_by,
            )
        )

        return task

    def move_to(self, new_status: TaskStatus, moved_by: UUID) -> None:
        """Перемещение статуса задачи (между колонками Kanban)"""

        # 1. Проверка возможности перехода
        if new_status not in ALLOWED_TRANSITIONS.get(self.status, []):
            raise InvalidStateError(
                f"Invalid status transition from {self.status} to {new_status}"
            )

        # 2. Обновление статуса
        old_status = self.status
        self.status = new_status
        self.updated_at = current_datetime()

        # 3. Если исполнитель приступил к работе, то установить время начала
        if new_status == TaskStatus.IN_PROGRESS and self.started_at is None:
            self.started_at = current_datetime()

        # 4. Если задача завершена, то установка времени завершения
        if new_status == TaskStatus.DONE and self.completed_at is None:
            self.completed_at = current_datetime()

        # 5. Регистрация доменного события
        self.register_event(
            TaskStatusMoved(
                task_id=self.id,
                ticket_id=self.ticket_id,
                old_status=old_status,
                new_status=new_status,
                moved_by=moved_by,
            )
        )

    def assign_to(self, assignee_id: UUID, assigned_by: UUID) -> None:
        """Назначение исполнителя на задачу"""
