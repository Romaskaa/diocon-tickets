from typing import Annotated

from datetime import date, datetime
from uuid import UUID

from fastapi import Body
from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt

from ..shared.schemas import Page
from .domain.vo import ProjectRole, ProjectStageStatus, ProjectStatus

NewProjectStagesOrder = Annotated[
    list[UUID], Body(..., embed=True, description="Новый порядок проведения этапов")
]


class ProjectBase(BaseModel):
    """Базовая схема проекта"""

    name: str = Field(
        ..., description="Наименование проекта", examples=["Корпоративный сайт компании"]
    )
    key: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Уникальный ключ проекта",
        examples=["PROJ", "MOB1"],
    )
    description: str | None = Field(
        None, description="Описание проекта (рекомендуется к заполнению)"
    )
    counterparty_id: UUID | None = Field(
        None, description="Контрагент для которого реализуется проект"
    )


class ProjectCreate(ProjectBase):
    """Схема для создания проекта"""


class ProjectMembershipResponse(BaseModel):
    """Участник проекта"""

    project_id: UUID = Field(..., description="ID проекта в котором состоит участник")
    project_role: ProjectRole = Field(..., description="Роль в проекте")
    user_id: UUID = Field(..., description="ID пользователя в системе")
    created_by: UUID = Field(..., description="ID пользователя, который добавил участника")
    created_at: datetime = Field(..., description="Дата добавления участника")
    is_active: bool = Field(..., description="Активен ли участник в проекте")


class ProjectStageCreate(BaseModel):
    """Создание нового этапа проекта"""

    name: str = Field(..., description="Название этапа")
    description: str | None = Field(
        None, description="Детальное описание (например, что будет выполнено в рамках этапа)"
    )
    order: PositiveInt | None = Field(
        ...,
        description="""\
        Порядковый номер этапа (все этапы должны выполняться по порядку).
        Если передан null - порядок этапа определиться автоматически.
        """
    )
    planned_start: date | None = Field(None, description="Запланированная дата начала этапа")
    planned_end: date | None = Field(None, description="Запланированная дата завершения этапа")


class ProjectStageUpdate(BaseModel):
    """Обновление этапа проекта"""

    name: str | None = Field(None, description="Название этапа")
    description: str | None = Field(
        None, description="Детальное описание (например, что будет выполнено в рамках этапа)"
    )
    responsible_id: UUID | None = Field(None, description="Ответственный за проведение этапа")
    completion_criteria: list[str] | None = Field(None, description="Критерии завершения")


class ProjectStagePlan(BaseModel):
    """Планирование этапа проекта"""

    planned_start: date = Field(..., description="Дата начала этапа")
    planned_end: date = Field(..., description="Плановая дата окончания этапа")


class ProjectStageResponse(BaseModel):
    """Этап проекта (логический блок в рамках которого выполняются работы)"""

    id: UUID = Field(..., description="ID этапа")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата последнего изменения")

    project_id: UUID = Field(..., description="ID проекта")
    name: str = Field(..., description="Название этапа")
    order: PositiveInt = Field(
        ..., description="Порядковый номер этапа (все этапы должны выполняться по порядку)"
    )
    status: ProjectStageStatus = Field(..., description="Текущий статус этапа")

    planned_start: date | None = Field(None, description="Запланированная дата начала этапа")
    planned_end: date | None = Field(None, description="Запланированная дата завершения этапа")

    started_at: datetime | None = Field(None, description="Дата начала")
    completed_at: datetime | None = Field(None, description="Дата завершения")
    responsible_id: UUID | None = Field(None, description="Ответственный за этап")
    description: str | None = Field(
        None, description="Детальное описание (например, что будет выполнено в рамках этапа"
    )
    completion_criteria: list[str] = Field(default_factory=list, description="Критерии приёмки")

    is_overdue: bool = Field(..., description="Просрочены ли сроки выполнения")
    planned_duration_days: NonNegativeInt | None = Field(
        None, description="Продолжительность этапа в днях"
    )


class ProjectResponse(ProjectBase):
    """API схема ответа для проекта"""

    id: UUID = Field(..., description="Уникальный ID проекта")
    created_at: datetime = Field(..., description="Дата создания проекта")
    updated_at: datetime = Field(..., description="Дата обновления проекта")

    owner_id: UUID = Field(..., description="Владелец проекта (обычно support и выше)")
    created_by: UUID = Field(..., description="ID пользователя создавшего проект")
    status: ProjectStatus = Field(..., description="Статус проекта")

    current_stage_id: UUID | None = Field(..., description="ID текущего этапа проекта")
    stages: list[ProjectStageResponse] = Field(default_factory=list, description="Этапы проекта")


class ProjectDetailedResponse(ProjectResponse):
    """Проект с детализированной информацией: участники, этапы, денормализованные поля"""

    memberships: Page[ProjectMembershipResponse] = Field(
        ..., description="Список участников проекта с пагинацией"
    )


class KeyCheckResult(BaseModel):
    """Результат проверки уникальности ключа"""

    available: bool = Field(..., description="Доступен ли ключ")
    suggestions: list[str] = Field(
        default_factory=list, description="Варианты, которые можно попробовать "
    )


class ProjectMembershipCreate(BaseModel):
    """Добавление участника проекта"""

    user_id: UUID = Field(..., description="ID пользователя, которого нужно добавить")
    project_role: ProjectRole = Field(..., description="Назначенная роль в проекте")
