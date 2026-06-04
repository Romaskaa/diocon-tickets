from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt

from ..iam.domain.vo import UserRole
from ..media.schemas import AttachmentResponse
from .domain.vo import (
    CommentType,
    ProjectRole,
    ProjectStatus,
    ReactionType,
    TicketPriority,
    TicketStatus,
)


class CommentResponse(BaseModel):
    """Схема API ответа для комментария"""

    id: UUID = Field(..., description="Уникальный ID комментария")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    ticket_id: UUID = Field(..., description="ID тикета к которому оставлен комментарий")
    author_id: UUID = Field(..., description="ID автора (тот кто написал комментарий)")
    author_role: UserRole = Field(..., description="Роль автора в системе")
    text: str = Field(..., description="Текст комментария")
    type: CommentType = Field(..., description="Тип комментария")
    parent_comment_id: UUID | None = Field(
        None, description="ID комментария, на который был сделан ответ"
    )
    reply_count: NonNegativeInt = Field(..., description="Количество ответов")
    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Медиа контент внутри тикета"
    )


class ReactionResponse(BaseModel):
    """Сводка реакций для одного комментария"""

    reaction_counts: dict[ReactionType, NonNegativeInt] = Field(
        default_factory=dict,
        description="Счётчик для каждой оставленной реакции",
        examples=[{ReactionType.LIKE: 17, ReactionType.IN_PROGRESS: 2, ReactionType.RESOLVED: 1}],
    )
    user_reactions: list[ReactionType] = Field(
        default_factory=list, description="Реакции, которые оставил текущий пользователь"
    )


class CommentWithReactionsResponse(CommentResponse, ReactionResponse):
    """Комментарий с реакциями"""


class HistoryEntryResponse(BaseModel):
    """Схема записи истории изменений"""

    created_at: datetime = Field(..., description="Дата записи")
    actor_id: UUID = Field(..., description="ID пользователя, который внёс изменения")
    action: str = Field(
        ...,
        description="Действие, которое было произведено над тикетом",
        examples=["created", "assigned", "status_changed"]
    )
    old_value: str | None = Field(None, description="Старое значение (до изменений)")
    new_value: str | None = Field(None, description="Новое значение")
    description: str = Field(..., description="Человеко-читаемое описание действия")


class Tag(BaseModel):
    """Теги для упрощения поиска и фильтрации"""

    name: str = Field(
        ..., description="Название тега", examples=["Инцидент", "Вопрос от пользователя"]
    )
    color: str = Field(..., description="Hex код цвета (для UI)", examples=["#0345fc", "#fc0303"])


class TicketBase(BaseModel):
    """Базовые поля для API схем тикета"""

    reporter_id: UUID = Field(..., description="ID пользователя - инициатора")
    title: str = Field(..., description="Заголовок")
    description: str = Field(..., description="Описание проблемы")
    priority: TicketPriority = Field(
        ..., description="Приоритет выполнения (чем выше приоритет, тем быстрее время реакции)",
    )
    project_id: UUID | None = Field(
        None, description="ID проекта, к которому нужно привязать тикет"
    )
    counterparty_id: UUID | None = Field(None, description="Контрагент к которому привязан тикет")
    product_id: UUID | None = Field(
        None, description="Программный продукт к которому привязан тикет"
    )
    tags: list[Tag] = Field(
        default_factory=list, description="Теги для упрощения поиска и фильтрации"
    )


class TicketPreview(BaseModel):
    """
    Схема превью тикета. Удобно для пагинации, списков, множественного просмотра.
    """

    id: UUID = Field(..., description="Уникальный ID тикета")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    created_by: UUID = Field(..., description="ID пользователя, который создал тикет")
    reporter_id: UUID = Field(..., description="ID пользователя - инициатора")
    number: str = Field(..., description="Номер тикета", examples=["РОМ-26-00012456"])
    title: str = Field(..., description="Заголовок тикета")
    status: TicketStatus = Field(..., description="Текущий статус")
    priority: TicketPriority = Field(..., description="Приоритет")


class TicketResponse(TicketBase):
    """API схема ответа тикета"""

    id: UUID = Field(..., description="Уникальный ID тикета")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    created_by_role: UserRole = Field(..., description="Роль пользователя, который создал тикет")
    created_by: UUID = Field(..., description="ID пользователя, который создал тикет")
    number: str = Field(..., description="Номер тикета", examples=["ROMASHKA-26-00012456"])
    status: TicketStatus = Field(..., description="Текущий статус")
    assigned_to: UUID | None = Field(None, description="Кому назначен тикет")
    closed_at: datetime | None = Field(None, description="Дата закрытия тикета")
    is_archived: bool = Field(..., description="Заархивирован ли тикет")

    attachments: list[AttachmentResponse] = Field(
        default_factory=list, description="Прикреплённые файлы"
    )
    history: list[HistoryEntryResponse] = Field(
        default_factory=list, description="История работы с тикетом"
    )


class TicketCreate(TicketBase):
    """
    Схема поддерживает 3 сценария создания тикета.
    В зависимости от переданных полей система определяет тип создаваемого тикета.

    ### 1. Внутренний тикет

    Создаётся, если **не переданы** ни проект, ни контрагент.
    Используется для задач внутри команды поддержки.

    ### 2. Тикет записывается контрагенту

    Создаётся, если передано поле: counterparty_id.
    Используется при обращении внешнего клиента.

    ### 3. Тикет в рамках проекта

    Создаётся, если передано поле: project_id.
    Используется для задач, связанных с конкретным проектом разработки.
    """

    priority: TicketPriority = Field(
        TicketPriority.MEDIUM,
        description="Приоритет выполнения (чем выше приоритет, тем быстрее время реакции)"
    )


class TicketFilter(BaseModel):
    """Параметры для фильтрации тикетов"""

    # Базовые фильтры
    reporter_id: UUID | None = Field(None, description="По инициатору")
    creator_id: UUID | None = Field(None, description="По создателю")
    project_id: UUID | None = Field(None, description="По проекту")
    counterparty_id: UUID | None = Field(None, description="По контрагенту")
    status: TicketStatus | None = Field(None, description="По статусу")
    priority: TicketPriority | None = Field(None, description="По приоритету")

    # Дополнительные фильтры
    tags: list[str] | None = Field(None, description="По тегам")
    search: str | None = Field(None, description="Полнотекстовый поиск")
    assigned_to: UUID | None = Field(None, description="По исполнителю, которому назначили тикет")
    created_after: datetime | None = Field(None, description="Создан после")
    created_before: datetime | None = Field(None, description="Создан до")


class TicketAssign(BaseModel):
    """Назначение тикета на пользователя"""

    assignee_id: UUID = Field(..., description="ID пользователя, на которого назначается тикет")


class TicketStatusChange(BaseModel):
    """Изменение статуса тикета"""

    status: TicketStatus = Field(..., description="Статус, который нужно установить")


class TicketEdit(BaseModel):
    """Редактирование тикета"""

    title: str | None = Field(None, description="Заголовок")
    description: str | None = Field(None, description="Описание")
    priority: TicketPriority | None = Field(None, description="Приоритет")
    tags: list[Tag] | None = Field(None, description="Теги")


class TicketPredict(BaseModel):
    """Авто-определение приоритетов + генерация тегов"""

    title: str = Field(..., description="Заголовок тикета")
    description: str = Field(..., description="Описание тикета")


class PredictionConfidence(BaseModel):
    """Уверенность в генерации"""

    priority: NonNegativeFloat = Field(
        ..., le=1.0, description="Уверенность в определении приоритета"
    )
    tags: NonNegativeFloat = Field(..., le=1.0, description="Уверенность в определении тегов")


class PredictionResponse(BaseModel):
    """API схема ответа с определённым приоритетом и сгенерированными тегами"""

    suggested_priority: TicketPriority = Field(..., description="Предложенный приоритет")
    suggested_tags: list[Tag] = Field(
        default_factory=list, min_length=1, max_length=10, description="Предложенные теги"
    )
    confidence: PredictionConfidence = Field(..., description="Уверенность в генерации")


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
    owner_id: UUID = Field(..., description="Владелец проекта (обычно support и выше)")


class ProjectCreate(ProjectBase):
    """Схема для создания проекта"""


class MembershipResponse(BaseModel):
    """Участник проекта"""

    user_id: UUID = Field(..., description="ID пользователя в системе")
    project_role: ProjectRole = Field(..., description="Роль в проекте")
    added_at: datetime = Field(..., description="Дата добавления в проект")
    added_by: UUID = Field(..., description="ID пользователя, который добавил участника")
    is_active: bool = Field(..., description="Активен ли участник п проекте")


class ProjectResponse(ProjectBase):
    """API схема ответа для проекта"""

    id: UUID = Field(..., description="Уникальный ID проекта")
    created_at: datetime = Field(..., description="Дата создания проекта")
    updated_at: datetime = Field(..., description="Дата обновления проекта")
    created_by: UUID = Field(..., description="ID пользователя создавшего проект")
    status: ProjectStatus = Field(..., description="Статус проекта")
    memberships: list[MembershipResponse] = Field(
        default_factory=list, description="Участники проекта"
    )


class KeyCheckResponse(BaseModel):
    """Результат проверки уникальности ключа"""

    available: bool = Field(..., description="Доступен ли ключ")
    suggestions: list[str] = Field(
        default_factory=list, description="Варианты, которые можно попробовать "
    )


class MemberAdd(BaseModel):
    """Добавление участника проекта"""

    user_id: UUID = Field(..., description="ID пользователя, которого нужно добавить")
    project_role: ProjectRole = Field(..., description="Назначенная роль в проекте")


class MembersAdd(BaseModel):
    """Добавление множества участников за один запрос"""

    members: list[MemberAdd] = Field(
        default_factory=list, description="Участники, которых нужно добавить в проект"
    )


class CommentCreate(BaseModel):
    """Создание комментария"""

    text: str = Field(..., description="Текст комментария")
    type: CommentType = Field(CommentType.PUBLIC, description="Тип комментария")


class CommentEdit(BaseModel):
    """Редактирование комментария"""

    text: str = Field(..., description="Новый текст комментария")
