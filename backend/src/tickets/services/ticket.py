from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...crm.domain.repo import CounterpartyRepository
from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.domain.repos import UserRepository
from ...iam.schemas import CurrentUser
from ...projects.domain.repos import ProjectRepository
from ...projects.domain.services import ProjectAccessService
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import NotFoundError
from ..domain.entities import Ticket
from ..domain.repos import TicketRepository
from ..domain.services import (
    can_archive_ticket,
    can_assign_to,
    can_change_status,
    can_create_ticket,
)
from ..domain.vo import ProjectKey, Tag, TicketNumber, TicketStatus
from ..mappers import map_ticket_to_response
from ..schemas import TicketCreate, TicketEdit, TicketResponse


@dataclass
class TicketCreationContext:
    """
    Необходимый контекст для создания тикета
    """

    project_id: UUID | None = None
    project_key: ProjectKey | None = None
    counterparty_id: UUID | None = None
    counterparty_name: str | None = None


class TicketService:
    def __init__(
            self,
            session: AsyncSession,
            ticket_repo: TicketRepository,
            project_repo: ProjectRepository,
            project_access_service: ProjectAccessService,
            user_repo: UserRepository,
            counterparty_repo: CounterpartyRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.ticket_repo = ticket_repo
        self.project_repo = project_repo
        self.user_repo = user_repo
        self.counterparty_repo = counterparty_repo
        self.project_access_service = project_access_service
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

        # 1. Тикет создаётся в рамках проекта
        if data.project_id is not None:
            project = await self.project_repo.read(data.project_id)
            if project is None:
                raise NotFoundError(f"Project with ID {data.project_id} not found")

            return TicketCreationContext(
                project_id=data.project_id,
                project_key=project.key,
                counterparty_id=project.counterparty_id,
                counterparty_name=None,
            )

        # 2. Тикет привязан к контрагенту
        if data.counterparty_id is not None:
            counterparty = await self.counterparty_repo.read(data.counterparty_id)
            if counterparty is None:
                raise NotFoundError(f"Counterparty with ID {data.counterparty_id} not found")

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

    async def create(self, data: TicketCreate, current_user: CurrentUser) -> TicketResponse:
        """Создание тикета"""

        # 1. Определение контекста создания тикета
        context = await self._determine_creation_context(data)

        # 2. Проверка прав на создание проекта
        permission = can_create_ticket(
            user_role=current_user.role,
            user_counterparty_id=current_user.counterparty_id,
            counterparty_id=context.counterparty_id,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Проверка прав на создание тикета внутри проекта
        if context.project_id is not None:
            permission = await self.project_access_service.can_create_ticket(
                project_id=context.project_id,
                user_id=current_user.user_id,
                user_role=current_user.role,
            )
            if not permission.allowed:
                raise PermissionDeniedError(permission.reason)

        # 4. Генерация уникального номера
        total_tickets = await self.ticket_repo.get_total(
            project_id=data.project_id, counterparty_id=data.counterparty_id
        )
        ticket_number = TicketNumber.create(
            total_tickets,
            project_key=context.project_key,
            counterparty_name=context.counterparty_name,
        )

        # 5. Создание и сохранение доменной сущности
        ticket = Ticket.create(
            ticket_number=ticket_number,
            created_by=current_user.user_id,
            created_by_role=current_user.role,
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
        await self.session.commit()

        # 6. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def edit(self, ticket_id: UUID, data: TicketEdit, edited_by: UUID) -> TicketResponse:
        """Редактирование тикета"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Редактирование и обновление сущности
        ticket.edit(
            edited_by=edited_by,
            title=data.title,
            description=data.description,
            priority=data.priority,
            tags=None if data.tags is None
            else [Tag(name=tag.name, color=tag.color) for tag in data.tags],
        )
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 3. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def archive(self, ticket_id: UUID, current_user: CurrentUser) -> TicketResponse:
        """Архивация тикета"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. проверка прав на архивацию тикета
        permission = can_archive_ticket(
            ticket=ticket, user_id=current_user.user_id, user_role=current_user.role
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Архивация тикета и обновление сущности
        ticket.archive(archived_by=current_user.user_id)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def assign_to(
            self, ticket_id: UUID, assignee_id: UUID, current_user: CurrentUser
    ) -> TicketResponse:
        """Назначение тикета на исполнителя"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Загрузка пользователя на которого назначается тикет
        assignee = await self.user_repo.read(assignee_id)
        if assignee is None:
            raise NotFoundError(f"User with ID {assignee_id} not found")

        # 3. Глобальная проверка прав на назначение исполнителя
        permission = can_assign_to(
            ticket=ticket,
            assignee_id=assignee_id,
            assignee_role=assignee.role,
            user_id=current_user.user_id,
            user_role=current_user.role,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 4. Если тикет принадлежит проекту, то проверка прав в проекте
        if ticket.project_id is not None:
            permission = await self.project_access_service.can_assign_ticket(
                project_id=ticket.project_id,
                assignee_id=assignee_id,
                user_id=current_user.user_id,
                user_role=current_user.role,
            )
            if not permission.allowed:
                raise PermissionDeniedError(permission.reason)

        # 5. Назначение исполнителя и обновление сущности
        ticket.assign_to(assignee_id=assignee_id, assigned_by=current_user.user_id)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 6. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def change_status(
            self, ticket_id: UUID, new_status: TicketStatus, current_user: CurrentUser
    ) -> TicketResponse:
        """Изменение статуса тикета"""

        # 1. Получение тикета и проверка на существование
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Проверка прав на изменение статуса
        permission = can_change_status(
            ticket=ticket,
            new_status=new_status,
            user_id=current_user.user_id,
            user_role=current_user.role,
            user_counterparty_id=current_user.counterparty_id,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 3. Внутри-проектная проверка прав
        if ticket.project_id is not None:
            permission = await self.project_access_service.can_change_ticket_status(
                project_id=ticket.project_id,
                ticket=ticket,
                new_status=new_status,
                user_id=current_user.user_id,
                user_role=current_user.role,
                user_counterparty_id=current_user.counterparty_id,
            )
            if not permission.allowed:
                raise PermissionDeniedError(permission.reason)

        # 4. Изменение статуса и обновление доменной сущности
        ticket.change_status(new_status=new_status, changed_by=current_user.user_id)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)
