from src.shared.schemas import Page

from .domain.entities import Feedback
from .schemas import FeedbackPageResponse, FeedbackResponse


def map_feedback_to_response(feedback: Feedback) -> FeedbackResponse:
    """
    Преобразовать доменный отзыв в API-схему.
    """

    return FeedbackResponse(
        id=feedback.id,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
        is_archived=feedback.is_deleted,
        ticket_id=feedback.ticket_id,
        author_id=feedback.author_id,
        rating=feedback.rating.value,
        comment=feedback.comment,
    )


def map_feedback_page_to_response(page: Page[Feedback]) -> FeedbackPageResponse:
    """
    Преобразовать страницу доменных отзывов в API-схему.
    """

    return page.to_response(map_feedback_to_response)