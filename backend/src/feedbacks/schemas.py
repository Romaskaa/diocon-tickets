from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """
    Схема создания отзыва по тикету.
    """

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Оценка качества обслуживания от 1 до 5",
    )
    comment: str | None = Field(
        None,
        description="Опциональный комментарий клиента",
    )


class FeedbackUpdate(BaseModel):
    """
    Схема обновления отзыва.
    """

    rating: int | None = Field(
        None,
        ge=1,
        le=5,
        description="Новая оценка качества обслуживания от 1 до 5",
    )
    comment: str | None = Field(
        None,
        description="Новый комментарий клиента",
    )


class FeedbackResponse(BaseModel):
    """
    API-представление отзыва.
    """

    id: UUID = Field(..., description="Уникальный ID отзыва")
    created_at: datetime = Field(..., description="Дата создания отзыва")
    updated_at: datetime = Field(..., description="Дата обновления отзыва")
    is_archived: bool = Field(..., description="Архивирован ли отзыв")

    ticket_id: UUID = Field(..., description="ID тикета, к которому относится отзыв")
    author_id: UUID = Field(..., description="ID клиента, который оставил отзыв")
    rating: int = Field(..., ge=1, le=5, description="Оценка качества обслуживания")
    comment: str | None = Field(None, description="Комментарий клиента")
