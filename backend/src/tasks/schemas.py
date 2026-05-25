from typing import Annotated, Literal

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import Body
from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt

from ..media.schemas import AttachmentResponse
from ..shared.schemas import Page
from ..tickets.domain.vo import Priority
from .domain.vo import TaskStatus

NewStatus = Annotated[
    TaskStatus, Body(..., embed=True, description="Новый статус задачи")
]
AssigneeId = Annotated[
    UUID,
    Body(..., embed=True, description="ID пользователя, которого нужна назначить исполнителем")
]
ReviewerId = Annotated[
    UUID,
    Body(..., embed=True, description="ID пользователя, который должен проверить задачу")
]


class TaskBase(BaseModel):
    """Базовая API схема задачи"""

    ticket_id: UUID | None = Field(None, description="Тикет на основе которого создана задача")
    project_id: UUID | None = Field(None, description="Проект в рамках которого создана задача")
    title: str = Field(..., description="Тема задачи")
    description: str | None = Field(None, description="Постановка задачи")
    priority: Priority = Field(..., description="Приоритет задачи")
    story_points: int | None = Field(
        None,
        ge=1,
        le=21,
        description="Оценка сложности задачи, где 1 очень легко, а 21 максимально сложно"
    )
    assignee_id: UUID | None = Field(None, description="Исполнитель задачи")
    reviewer_id: UUID | None = Field(None, description="Ответственный за задачу")
    estimated_hours: Decimal | None = Field(
        None, description="Предварительная оценка трудозатрат в часах"
    )
    due_date: date | None = Field(None, description="Срок выполнения (deadline)")


class TaskCreate(TaskBase):
    """API схема для создания задачи"""

    mark_as_todo: bool = Field(False, description="Готова ли задача к выполнению")


class TaskResponse(TaskBase):
    """API схема ответа задачи"""

    id: UUID = Field(..., description="Уникальный ID задачи")
    created_at: datetime = Field(..., description="Дата создания задачи")
    updated_at: datetime = Field(..., description="Дата обновления задачи")
    is_archived: bool = Field(..., description="Перенесена ли задача в архив")
    number: str = Field(
        ...,
        description="Уникальный номер задачи",
        examples=["PRJ-26-00000001-001", "TASK-001"]
    )
    status: TaskStatus = Field(..., description="Текущий cтатус задачи")
    actual_hours: Decimal = Field(..., description="Потрачено часов (факт)")
    started_at: datetime | None = Field(None, description="Дата начала выполнения задачи")
    completed_at: datetime | None = Field(None, description="Дата завершения задачи")
    created_by: UUID = Field(..., description="Пользователь создавший задачу")
    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Медиа контент приложенный к задаче"
    )


class TaskEdit(BaseModel):
    """API схема для редактирования задачи"""

    title: str | None = Field(None, description="Тема задачи")
    description: str | None = Field(None, description="Формулировка задачи")
    priority: Priority | None = Field(None, description="")
    story_points: int | None = Field(
        None,
        ge=1,
        le=21,
        description="Story points для оценки сложности задачи"
    )
    estimated_hours: NonNegativeFloat | None = Field(
        None, description="Предварительное время выполнения"
    )
    due_date: date | None = Field(None, description="Срок выполнения (deadline)")


class TaskReview(BaseModel):
    """API схема для ревью задачи"""

    action: Literal["approve", "reject"] = Field(..., description="Принять или отклонить задачу")


class TaskViewResponse(BaseModel):
    """Облегчённая модель для представления задачи"""

    id: UUID = Field(..., description="Уникальный ID задачи")
    created_at: datetime = Field(..., description="Дата создания задачи")
    updated_at: datetime = Field(..., description="Дата обновления задачи")

    number: str = Field(
        ..., description="Уникальный номер задачи", examples=["PRJ-26-00000001-001", "TASK-001"]
    )
    title: str = Field(..., description="Тема задачи")
    priority: Priority = Field(..., description="Приоритет задачи")
    story_points: int | None = Field(
        None,
        ge=1,
        le=21,
        description="Оценка сложности задачи, где 1 очень легко, а 21 максимально сложно",
    )
    assignee_id: UUID | None = Field(None, description="Исполнитель задачи")
    status: TaskStatus = Field(..., description="Текущий cтатус задачи")
    due_date: date | None = Field(None, description="Срок выполнения (deadline)")

    ticket_id: UUID | None = Field(None, description="Тикет на основе которого создана задача")
    project_id: UUID | None = Field(None, description="Проект в рамках которого создана задача")


# ============================== Канбан доски ==============================


class KanbanContext(BaseModel):
    type: Literal[
        "project",
        "ticket",
        "internal",
        "assignee",
        "my",
    ] = Field(..., description="Контекст просмотра задач на Kanban доске")


class ProjectKanbanContext(KanbanContext):
    type: Literal["project", "ticket", "internal", "assignee", "my"] = "project"
    project_id: UUID = Field(..., description="ID проекта")


class TicketKanbanContext(KanbanContext):
    type: Literal["project", "ticket", "internal", "assignee", "my"] = "ticket"
    ticket_id: UUID = Field(..., description="ID тикета")


class InternalKanbanContext(KanbanContext):
    type: Literal["project", "ticket", "internal", "assignee", "my"] = "internal"


class AssigneeKanbanContext(KanbanContext):
    type: Literal["project", "ticket", "internal", "assignee", "my"] = "assignee"
    assignee_id: UUID = Field(..., description="ID исполнителя задачи")


class MyTasksKanbanContext(KanbanContext):
    type: Literal["project", "ticket", "internal", "assignee", "my"] = "my"


KanbanContextType = (
        ProjectKanbanContext
        | TicketKanbanContext
        | InternalKanbanContext
        | AssigneeKanbanContext
        | MyTasksKanbanContext
)


class KanbanColumn(BaseModel):
    """Колонка канбан доски, соответствующая статусу задачи"""

    status: TaskStatus = Field(..., description="Статус задачи")
    label: str = Field(..., description="Русское название статуса для UI", examples=["В работе"])
    tasks: Page[TaskViewResponse] = Field(..., description="Список задач")


class KanbanBoard(BaseModel):
    """Канбан доска с задачами"""

    context: KanbanContextType = Field(..., description="Контекст просмотра доски")
    columns: list[KanbanColumn] = Field(default_factory=list, description="Колонки Kanban")

    total_tasks: NonNegativeInt = Field(..., description="Всего задач")


@dataclass(frozen=True)
class KanbanFilters:
    """Фильтры для работы с канбан доской"""

    priorities: list[Priority] | None = None
    overdue_only: bool = False
