from typing import Any, TypedDict

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .domain.vo import NotificationType


class NotificationResponse(BaseModel):
    """Схема API ответа уведомления"""

    id: UUID = Field(..., description="Уникальный ID уведомления")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    user_id: UUID = Field(..., description="Пользователь, которому адресовано уведомление")
    title: str = Field(..., description="Заголовок")
    message: str = Field(..., description="Детальное сообщение")
    type: NotificationType = Field(..., description="Тип события, которое стригерило уведомление")
    read: bool = Field(..., description="Прочитано ли уведомление")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Дополнительные контекстные данные"
    )


class UnreadCountOut(TypedDict):
    unread_count: int
