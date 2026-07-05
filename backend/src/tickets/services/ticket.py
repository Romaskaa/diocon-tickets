from dataclasses import dataclass
from uuid import UUID

from src.activity_logs.recorder import ActivityLogRecorder
from src.crm.domain.entities import Counterparty
from src.crm.domain.repo import CounterpartyRepository
from src.iam.domain.authz import Subject
from src.iam.domain.entities import User
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.repos import UserRepository
from src.projects.domain.entities import Project
from src.projects.domain.repos import ProjectRepository
from src.shared.domain.events import EventPublisher
from src.shared.domain.repos import UnitOfWork, finalize, get_or_raise_404

from ..domain.authz import TicketAuthZService
from ..domain.entities import Ticket
from ..domain.repos import TicketRepository
from ..domain.vo import ProjectKey, Tag, TicketNumber
from ..mappers import map_ticket_to_response
from ..schemas import TicketCreate, TicketEdit, TicketResponse


@dataclass(frozen=True)
class TicketCreationContext:
    """
    Необходимый контекст для создания тикета.
    """

    project_id: UUID | None = None
    project_key: ProjectKey | None = None
    counterparty_id: UUID | None = None
    counterparty_name: str | None = None


class TicketService:
    def __init__(
            self,
            uow: UnitOfWork,
            ticket_repo: TicketRepository,
            project_repo: ProjectRepository,
            user_repo: UserRepository,
            counterparty_repo: CounterpartyRepository,
            ticket_authz_service: TicketAuthZService,
            activity_log_recorder: ActivityLogRecorder,
            event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.ticket_repo = ticket_repo
        self.project_repo = project_repo
        self.user_repo = user_repo
        self.counterparty_repo = counterparty_repo
        self.ticket_authz_service = ticket_authz_service
        self.activity_log_recorder = activity_log_recorder
        self.event_publisher = event_publisher

    async def _determine_creation_context(self, data: TicketCreate) -> TicketCreationContext:
        """
        Определение контекста создания тикета и валидация входных данных

        - Если указан project_id, то counterparty_id подтягивается из проекта.
        - Если указан counterparty_id, то используется напрямую.
        - Если не указан ни project_id, ни counterparty_id, то контекст зануляется.
        """

        if data.project_id is not None and data.counterparty_id is not None:
            raise ValueError("Only one of the project or counterparty must be specified")

        if data.project_id is not None:
            project = await get_or_raise_404(self.project_repo.read, data.project_id, Project)

            return TicketCreationContext(
                project_id=data.project_id,
                project_key=project.key,
                counterparty_id=project.counterparty_id,
                counterparty_name=None,
            )

        if data.counterparty_id is not None:
            counterparty = await get_or_raise_404(
                self.counterparty_repo.read, data.counterparty_id, Counterparty,
            )

            return TicketCreationContext(
                project_id=None,
                project_key=None,
                counterparty_id=counterparty.id,
                counterparty_name=counterparty.name,
            )

        return TicketCreationContext(
            project_id=None,
            project_key=None,
            counterparty_id=None,
            counterparty_name=None,
        )

    async def create(self, data: TicketCreate, current_subject: Subject) -> TicketResponse:

        context = await self._determine_creation_context(data)

        permission = await self.ticket_authz_service.can_create_ticket(
            subject=current_subject,
            counterparty_id=context.counterparty_id,
            project_id=context.project_id,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        total = await self.ticket_repo.get_total(
            project_id=data.project_id, counterparty_id=data.counterparty_id
        )
        number = TicketNumber.create(
            total,
            project_key=context.project_key,
            counterparty_name=context.counterparty_name,
        )

        ticket = Ticket.create(
            number=number,
            created_by=current_subject.id,
            created_by_role=...,
            reporter_id=data.reporter_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            project_id=context.project_id,
            counterparty_id=context.counterparty_id,
            product_id=data.product_id,
            tags=[Tag(name=tag.name, color=tag.color) for tag in data.tags],
        )
        await self.ticket_repo.create(ticket)
        await finalize(
            self.uow, ticket,
            activity_recorder=self.activity_log_recorder,
            event_publisher=self.event_publisher,
        )

        return map_ticket_to_response(ticket)

    async def edit(
            self, ticket_id: UUID, data: TicketEdit, current_subject: Subject,
    ) -> TicketResponse:

        ticket = await get_or_raise_404(self.ticket_repo.read, ticket_id, Ticket)

        permission = self.ticket_authz_service.can_edit_ticket(
            subject=current_subject, ticket=ticket,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        tags = (
            None if data.tags is None else
            [Tag(name=tag.name, color=tag.color) for tag in data.tags]
        )
        ticket.edit(
            edited_by=current_subject.id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            tags=tags,
        )
        await self.ticket_repo.update(ticket)
        await finalize(
            self.uow, ticket,
            activity_recorder=self.activity_log_recorder,
            event_publisher=self.event_publisher,
        )

        return map_ticket_to_response(ticket)

    async def archive(self, ticket_id: UUID, current_subject: Subject) -> TicketResponse:
        """
        Перенести заявку в архив.
        """

        ticket = await get_or_raise_404(self.ticket_repo.read, ticket_id, Ticket)

        permission = await self.ticket_authz_service.can_archive_ticket(
            subject=current_subject, ticket=ticket,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        ticket.archive(archived_by=current_subject.id)
        await self.ticket_repo.update(ticket)
        await finalize(
            self.uow, ticket,
            activity_recorder=self.activity_log_recorder,
            event_publisher=self.event_publisher,
        )

        return map_ticket_to_response(ticket)

    async def assign(
            self, ticket_id: UUID, assignee_id: UUID, current_subject: Subject,
    ) -> TicketResponse:
        """
        Назначить исполнителя на заявку.
        """

        ticket = await get_or_raise_404(self.ticket_repo.read, ticket_id, Ticket)
        assignee = await get_or_raise_404(self.user_repo.read, assignee_id, User)

        permission = await self.ticket_authz_service.can_assign_ticket(
            subject=current_subject, ticket=ticket, assignee=assignee,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        ticket.assign(assignee_id=assignee_id, assigned_by=current_subject.id)
        await self.ticket_repo.update(ticket)
        await finalize(
            self.uow, ticket,
            activity_recorder=self.activity_log_recorder,
            event_publisher=self.event_publisher,
        )

        return map_ticket_to_response(ticket)
