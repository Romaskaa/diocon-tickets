from uuid import UUID

from src.iam.domain.authz import Subject
from src.iam.domain.exceptions import PermissionDeniedError
from src.shared.domain.events import EventPublisher
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.domain.repos import UnitOfWork, finalize, get_or_raise_404
from src.shared.schemas import Page, Pagination
from src.tickets.domain.entities import Ticket
from src.tickets.domain.repos import TicketRepository

from ..domain.authz import FeedbackAuthZService
from ..domain.entities import Feedback
from ..domain.repos import FeedbackFilters, FeedbackRepository
from ..mappers import map_feedback_page_to_response, map_feedback_to_response
from ..schemas import FeedbackCreate, FeedbackResponse, FeedbackUpdate


class FeedbackService:
    """
    Application service для сценариев работы с отзывами.
    """

    def __init__(
            self,
            uow: UnitOfWork,
            feedback_repo: FeedbackRepository,
            ticket_repo: TicketRepository,
            authz_service: FeedbackAuthZService,
            event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.feedback_repo = feedback_repo
        self.ticket_repo = ticket_repo
        self.authz_service = authz_service
        self.event_publisher = event_publisher

    async def create_for_ticket(
            self,
            ticket_id: UUID,
            data: FeedbackCreate,
            current_subject: Subject,
    ) -> FeedbackResponse:
        """
        Создать отзыв по закрытому тикету.
        """

        ticket = await get_or_raise_404(self.ticket_repo.read, ticket_id, Ticket)

        permission = self.authz_service.can_create_feedback(
            subject=current_subject,
            ticket=ticket,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)
        
        existing_feedback = await self.feedback_repo.get_by_ticket(ticket_id)
        if existing_feedback is not None:
            raise AlreadyExistsError(f"Feedback for ticket {ticket_id} already exists")
        
        feedback = Feedback.create(
            ticket_id=ticket_id,
            author_id=current_subject.id,
            rating=data.rating,
            comment=data.comment,
        )

        await self.feedback_repo.create(feedback)
        await finalize(self.uow, feedback, event_publisher=self.event_publisher)

        return map_feedback_to_response(feedback)
    
    async def get_by_ticket(
            self,
            ticket_id: UUID,
            current_subject: Subject,
    ) -> FeedbackResponse:
        """
        Получить активный отзыв по тикету.
        """

        feedback = await self.feedback_repo.get_by_ticket(ticket_id)
        if feedback is None:
            raise NotFoundError(f"Feedback for ticket {ticket_id} not found")
        
        permission = self.authz_service.can_view_feedback(
            subject=current_subject,
            feedback=feedback,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)
        
        return map_feedback_to_response(feedback)
    
    async def get_feedbacks(
            self,
            pagination: Pagination,
            filters: FeedbackFilters,
            current_subject: Subject,
    ) -> Page[FeedbackResponse]:
        """
        Получить список активных отзывов.
        """

        permission = self.authz_service.can_view_feedback(current_subject)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)
        
        page = await self.feedback_repo.paginate(
            pagination=pagination,
            filters=filters,
        )

        return map_feedback_page_to_response(page)
    
    async def update(
            self,
            feedback_id: UUID,
            data: FeedbackUpdate,
            current_subject: Subject,
    ) -> FeedbackResponse:
        """
        Обновить оценку или комментарий отзыва.
        """

        feedback = await get_or_raise_404(self.feedback_repo.read, feedback_id, Feedback)
        if feedback.is_deleted:
            raise NotFoundError(f"Feedback with ID {feedback_id} not found")

        permission = self.authz_service.can_update_feedback(
            subject=current_subject,
            feedback=feedback,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)
        
        feedback.edit(
            rating=data.rating,
            comment=data.comment,
        )

        await self.feedback_repo.update(feedback)
        await finalize(self.uow, feedback, event_publisher=self.event_publisher)

        return map_feedback_to_response(feedback)
    
    async def archive(
            self,
            feedback_id: UUID,
            current_subject: Subject,
    ) -> FeedbackResponse:
        """
        Архивировать отзыв через soft-delete.
        """

        feedback = await get_or_raise_404(self.feedback_repo.read, feedback_id, Feedback)
        if feedback.is_deleted:
            raise NotFoundError(f"Feedback with ID {feedback_id} not found")

        permission = self.authz_service.can_archive_feedback(
            subject=current_subject,
            feedback=feedback,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)
        
        feedback.archive()

        await self.feedback_repo.update(feedback)
        await finalize(self.uow, feedback, event_publisher=self.event_publisher)

        return map_feedback_to_response(feedback)