from uuid import UUID

from fastapi import APIRouter, status

from src.iam.dependencies import CurrentSubjectDep
from src.shared.dependencies import PaginationDep

from .dependencies import FeedbackFiltersDep, FeedbackServiceDep
from .schemas import (
    FeedbackCreate,
    FeedbackPageResponse,
    FeedbackResponse,
    FeedbackUpdate,
)

router = APIRouter(tags=["Отзывы"])


@router.post(
    path="/tickets/{ticket_id}/feedback",
    status_code=status.HTTP_201_CREATED,
    response_model=FeedbackResponse,
    summary="Оставить отзыв по тикету",
)
async def create_feedback(
    ticket_id: UUID,
    data: FeedbackCreate,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackResponse:
    return await service.create_for_ticket(
        ticket_id=ticket_id,
        data=data,
        current_subject=current_subject,
    )


@router.get(
    path="/tickets/{ticket_id}/feedback",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackResponse,
    summary="Получить отзыв по тикету",
)
async def get_feedback_by_ticket(
    ticket_id: UUID,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackResponse:
    return await service.get_by_ticket(
        ticket_id=ticket_id,
        current_subject=current_subject,
    )


@router.get(
    path="/feedbacks",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackPageResponse,
    summary="Получить список отзывов",
)
async def list_feedbacks(
    pagination: PaginationDep,
    filters: FeedbackFiltersDep,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackPageResponse:
    return await service.list_feedbacks(
        pagination=pagination,
        filters=filters,
        current_subject=current_subject,
    )


@router.patch(
    path="/feedbacks/{feedback_id}",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackResponse,
    summary="Обновить отзыв",
)
async def update_feedback(
    feedback_id: UUID,
    data: FeedbackUpdate,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackResponse:
    return await service.update(
        feedback_id=feedback_id,
        data=data,
        current_subject=current_subject,
    )


@router.delete(
    path="/feedbacks/{feedback_id}",
    status_code=status.HTTP_200_OK,
    response_model=FeedbackResponse,
    summary="Архивировать отзыв",
)
async def archive_feedback(
    feedback_id: UUID,
    current_subject: CurrentSubjectDep,
    service: FeedbackServiceDep,
) -> FeedbackResponse:
    return await service.archive(
        feedback_id=feedback_id,
        current_subject=current_subject,
    )