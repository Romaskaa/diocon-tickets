from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from src.media.domain.entities import Attachment
from src.shared.domain.entities import Entity
from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError
from src.shared.domain.vo import Priority, Tag
from src.shared.utils.time import current_datetime

from .consts import ALLOWED_ASSIGN_STATUSES, ALLOWED_EDIT_STATUSES, ALLOWED_STATUS_TRANSITIONS
from .events import (
    TaskArchived,
    TaskAssigned,
    TaskCreated,
    TaskReviewRequested,
    TaskStatusChanged,
    TaskUnassigned,
)
from .vo import StoryPoints, TaskNumber, TaskStatus


@dataclass(kw_only=True)
class Task(Entity):
    """
    Задача для сотрудника.
    Используется для детализации работ, например по большому тикету.
    """

    ticket_id: UUID | None = None
    project_id: UUID | None = None

    number: TaskNumber
    title: str
    description: str | None = None

    status: TaskStatus
    priority: Priority
    story_points: StoryPoints | None = None

    assignee_id: UUID | None = None
    reviewer_id: UUID | None = None

    estimated_hours: Decimal | None = None
    actual_hours: Decimal = Decimal(0)

    due_date: date | None = None  # Срок выполнения
    started_at: datetime | None = None
    completed_at: datetime | None = None

    created_by: UUID

    tags: set[Tag] = field(default_factory=set)

    attachments: list[Attachment] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Task title cannot be empty")

        if self.description is not None and not self.description.strip():
            raise ValueError("Task description cannot be empty")

        # Задача не может быть в процессе выполнения без исполнителя
        if self.status == TaskStatus.IN_PROGRESS and self.assignee_id is None:
            raise InvariantViolationError(
                "Task cannot be in 'IN_PROGRESS' status without an assignee"
            )

        # Завершённая задача должна иметь дату завершения
        if self.status == TaskStatus.DONE and self.completed_at is None:
            raise InvariantViolationError("Task in 'DONE' status must have completed_at")

    @classmethod
    def create(
            cls,
            number: TaskNumber,
            title: str,
            created_by: UUID,
            description: str | None = None,
            priority: Priority = Priority.MEDIUM,
            ticket_id: UUID | None = None,
            project_id: UUID | None = None,
            due_date: date | None = None,
            estimated_hours: Decimal | None = None,
            tags: list[Tag] | None = None,
    ) -> "Task":
        task_id = uuid4()
        task = cls(
            id=task_id,
            ticket_id=ticket_id,
            project_id=project_id,
            number=number,
            title=title.strip(),
            description=None if description is None else description.strip(),
            status=TaskStatus.BACKLOG,
            priority=priority,
            due_date=due_date,
            estimated_hours=None if estimated_hours is None else Decimal(estimated_hours),
            created_by=created_by,
            tags={} if tags is None else set(tags),
        )
        task.register_event(
            TaskCreated(
                task_id=task_id,
                ticket_id=ticket_id,
                title=title,
                created_by=created_by,
            )
        )
        return task

    def change_status(self, new_status: TaskStatus, changed_by: UUID) -> None:
        """
        Изменение статуса задачи.
        """

        if new_status == self.status:
            return

        allowed_next_statuses = ALLOWED_STATUS_TRANSITIONS.get(new_status, [])
        if new_status not in allowed_next_statuses:
            raise InvalidStateError(
                f"Invalid status transition from {self.status} to {new_status}. "
                f"Allowed transitions: {', '.join(allowed_next_statuses)}."
            )

        # Задача не может быть в работе без назначенного исполнителя
        if new_status == TaskStatus.IN_PROGRESS and self.assignee_id is None:
            raise InvariantViolationError(
                "Task cannot be in 'IN_PROGRESS' status without an assignee"
            )

        old_status = self.status
        self.status = new_status
        self.updated_at = current_datetime()

        # Снятие исполнителя при переводе в начальный статус
        if new_status in {TaskStatus.BACKLOG, TaskStatus.TODO}:
            old_assignee = self.assignee_id
            self.assignee_id = None
            self.register_event(
                TaskUnassigned(
                    task_id=self.id,
                    number=self.number,
                    old_assignee=old_assignee,
                    unassigned_by=changed_by,
                )
            )

        # Сброс ревьювера при возврате в работу
        if new_status in {TaskStatus.IN_PROGRESS, TaskStatus.TODO, TaskStatus.BACKLOG}:
            self.reviewer_id = None

        if new_status == TaskStatus.IN_PROGRESS and self.started_at is None:
            self.started_at = current_datetime()

        if new_status == TaskStatus.DONE and self.completed_at is None:
            self.completed_at = current_datetime()

        if old_status == TaskStatus.DONE and new_status != TaskStatus.DONE:
            self.completed_at = None

        self.updated_at = current_datetime()
        self.register_event(
            TaskStatusChanged(
                task_id=self.id,
                ticket_id=self.ticket_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
            )
        )

    def assign_to(self, assignee_id: UUID, assigned_by: UUID) -> None:
        """Назначение исполнителя на задачу"""

        # 1. Если исполнитель не переназначен, то состояние не меняется
        if self.assignee_id == assignee_id:
            return

        # 2. Проверка валидный статус
        if self.status not in ALLOWED_ASSIGN_STATUSES:
            raise InvalidStateError(
                f"Cannot assign task in status '{self.status.value}'. "
                f"Allowed statuses: {', '.join(s.value for s in ALLOWED_ASSIGN_STATUSES)}"
            )

        # 3. Назначение исполнителя
        old_assignee = self.assignee_id
        self.assignee_id = assignee_id
        self.updated_at = current_datetime()

        # 4. Регистрация доменного события
        self.register_event(
            TaskAssigned(
                task_id=self.id,
                ticket_id=self.ticket_id,
                old_assignee=old_assignee,
                new_assignee=assignee_id,
                assigned_by=assigned_by,
            )
        )

    def edit(  # noqa: C901
            self,
            *,
            title: str | None = None,
            description: str | None = None,
            priority: Priority | None = None,
            story_points: int | None = None,
            estimated_hours: Decimal | None = None,
            due_date: date | None = None,
    ) -> None:
        """Редактирование задачи"""

        # 1. Редактирование задачи разрешено только в начальных статусах
        if self.status not in ALLOWED_EDIT_STATUSES:
            raise InvalidStateError(
                f"Cannot edit task in status '{self.status.value}'. "
                f"Editing is only allowed in: "
                f"{', '.join(status.value for status in ALLOWED_EDIT_STATUSES)}"
            )

        # 2. Нельзя редактировать архивированную задачу
        if self.is_deleted:
            raise InvalidStateError("Cannot edit deleted task")

        # 3. Применение изменений
        is_edited = False

        if title is not None:
            if not title.strip():
                raise ValueError("Task title cannot be empty")

            self.title = title.strip()
            is_edited = True

        if description is not None:
            if not description.strip():
                raise ValueError("Task description cannot be empty")

            self.description = description.strip()
            is_edited = True

        if priority is not None and priority != self.priority:
            self.priority = priority
            is_edited = True

        if story_points is not None:
            new_story_points = StoryPoints(story_points)

            if self.story_points != new_story_points:
                self.story_points = new_story_points
                is_edited = True

        if estimated_hours is not None:
            if estimated_hours < 0:
                raise ValueError("Estimated hours cannot be negative")

            if estimated_hours != self.estimated_hours:
                self.estimated_hours = estimated_hours
                is_edited = True

        if due_date is not None and due_date != self.due_date:
            self.due_date = due_date
            is_edited = True

        if is_edited:
            self.updated_at = current_datetime()

    def add_actual_hours(self, hours: Decimal) -> None:
        """
        Добавление факта затраченных часов
        """

        if hours <= 0:
            raise ValueError("Hours must be positive")

        if self.is_deleted:
            raise InvalidStateError("Cannot add hours to archived task")

        self.actual_hours += hours
        self.updated_at = current_datetime()

    def request_review(self, reviewer_id: UUID, requested_by: UUID) -> None:
        """
        Запросить ревью задачи
        """

        # Исполнитель не может проверять свою задачу
        if self.assignee_id == reviewer_id:
            raise ValueError("Reviewer cannot be the same as assignee")

        # Назначение ответственного за задачу
        old_reviewer = self.reviewer_id
        self.reviewer_id = reviewer_id
        self.updated_at = current_datetime()

        # Переход в статус TO_REVIEW, если задача была в IN_PROGRESS
        self.change_status(TaskStatus.TO_REVIEW, requested_by)

        self.register_event(
            TaskReviewRequested(
                task_id=self.id,
                ticket_id=self.ticket_id,
                reviewer_id=reviewer_id,
                requested_by=requested_by,
                old_reviewer=old_reviewer,
            )
        )

    def approve_review(self, approved_by: UUID) -> None:
        """
        Согласовать задачу (проверяющий проверил задачу).
        """

        self.change_status(TaskStatus.DONE, approved_by)

    def reject_review(self, rejected_by: UUID) -> None:
        """
        Отклонить задачу (вернуть на доработку).
        """

        self.change_status(TaskStatus.IN_PROGRESS, rejected_by)

    def archive(self, archived_by: UUID) -> None:
        """Архивирование/Soft-delete задачи"""

        # 1. При повторном архивировании не должно меняться состояние
        if self.is_deleted:
            return

        # 2. Изменение состояние сущности
        self.deleted_at = current_datetime()

        self.register_event(
            TaskArchived(
                task_id=self.id,
                ticket_id=self.ticket_id,
                created_by=self.created_by,
                archived_by=archived_by,
            )
        )
