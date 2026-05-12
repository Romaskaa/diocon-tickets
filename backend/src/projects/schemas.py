from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..shared.schemas import Page
from .domain.vo import ProjectRole, ProjectStatus


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


class MembershipResponse(BaseModel):
    """Участник проекта"""

    user_id: UUID = Field(..., description="ID пользователя в системе")
    project_role: ProjectRole = Field(..., description="Роль в проекте")
    added_at: datetime = Field(..., description="Дата добавления в проект")
    added_by: UUID = Field(..., description="ID пользователя, который добавил участника")
    is_active: bool = Field(..., description="Активен ли участник в проекте")


class ProjectResponse(ProjectBase):
    """API схема ответа для проекта"""

    id: UUID = Field(..., description="Уникальный ID проекта")
    created_at: datetime = Field(..., description="Дата создания проекта")
    updated_at: datetime = Field(..., description="Дата обновления проекта")
    owner_id: UUID = Field(..., description="Владелец проекта (обычно support и выше)")
    created_by: UUID = Field(..., description="ID пользователя создавшего проект")
    status: ProjectStatus = Field(..., description="Статус проекта")


class ProjectDetailedResponse(ProjectResponse):
    """Детальный API ответ проекта"""

    memberships: Page[MembershipResponse] = Field(..., description="Список участников проекта")


class KeyCheckResult(BaseModel):
    """Результат проверки уникальности ключа"""

    available: bool = Field(..., description="Доступен ли ключ")
    suggestions: list[str] = Field(
        default_factory=list, description="Варианты, которые можно попробовать "
    )


class MemberCreate(BaseModel):
    """Добавление участника проекта"""

    user_id: UUID = Field(..., description="ID пользователя, которого нужно добавить")
    project_role: ProjectRole = Field(..., description="Назначенная роль в проекте")


class MembersCreate(BaseModel):
    """Добавление множества участников за один запрос"""

    members: list[MemberCreate] = Field(
        default_factory=list, description="Участники, которых нужно добавить в проект"
    )
