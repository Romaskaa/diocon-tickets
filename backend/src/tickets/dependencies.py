from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query

from ..crm.dependencies import CounterpartyRepoDep
from ..iam.dependencies import CurrentUserDep, UserRepoDep
from ..iam.domain.exceptions import PermissionDeniedError
from ..iam.domain.vo import UserRole
from ..shared.dependencies import EventPublisherDep, SessionDep
from .domain.repos import (
    CommentRepository,
    ProjectRepository,
    ReactionRepository,
    TicketRepository,
)
from .domain.vo import TicketPriority, TicketStatus
from .infra.repos import (
    SqlCommentRepository,
    SqlProjectRepository,
    SqlReactionRepository,
    SqlTicketRepository,
)
from .schemas import TicketFilter
from .services import CommentService, ProjectService, ReactionService, TicketService


def get_ticket_repo(session: SessionDep) -> TicketRepository:
    return SqlTicketRepository(session)


def get_comment_repo(session: SessionDep) -> CommentRepository:
    return SqlCommentRepository(session)


def get_project_repo(session: SessionDep) -> ProjectRepository:
    return SqlProjectRepository(session)


def get_reaction_repo(session: SessionDep) -> ReactionRepository:
    return SqlReactionRepository(session)


ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repo)]
TicketRepoDep = Annotated[TicketRepository, Depends(get_ticket_repo)]
CommentRepoDep = Annotated[CommentRepository, Depends(get_comment_repo)]
ReactionRepoDep = Annotated[ReactionRepository, Depends(get_reaction_repo)]


def get_project_service(
        session: SessionDep, repository: ProjectRepoDep, event_publisher: EventPublisherDep
) -> ProjectService:
    return ProjectService(session, repository=repository, event_publisher=event_publisher)


def get_ticket_service(
        session: SessionDep,
        counterparty_repo: CounterpartyRepoDep,
        ticket_repo: TicketRepoDep,
        project_repo: ProjectRepoDep,
        user_repo: UserRepoDep,
        event_publisher: EventPublisherDep
) -> TicketService:
    return TicketService(
        session,
        counterparty_repo=counterparty_repo,
        ticket_repo=ticket_repo,
        project_repo=project_repo,
        user_repo=user_repo,
        event_publisher=event_publisher
    )


def get_comment_service(
        session: SessionDep,
        ticket_repo: TicketRepoDep,
        comment_repo: CommentRepoDep,
        reaction_repo: ReactionRepoDep,
        event_publisher: EventPublisherDep
) -> CommentService:
    return CommentService(
        session=session,
        ticket_repo=ticket_repo,
        comment_repo=comment_repo,
        reaction_repo=reaction_repo,
        event_publisher=event_publisher
    )


def get_reaction_service(
        session: SessionDep,
        comment_repo: CommentRepoDep,
        reaction_repo: ReactionRepoDep,
        event_publisher: EventPublisherDep,
) -> ReactionService:
    return ReactionService(
        session=session,
        comment_repo=comment_repo,
        reaction_repo=reaction_repo,
        event_publisher=event_publisher
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
ReactionServiceDep = Annotated[ReactionService, Depends(get_reaction_service)]


def get_ticket_filters(
        current_user: CurrentUserDep,
        # Базовые фильтры
        reporter_id: Annotated[
            UUID | None, Query(..., description="По инициатору")
        ] = None,
        created_by: Annotated[
            UUID | None, Query(..., description="По фактическому создателю")
        ] = None,
        project_id: Annotated[
            UUID | None, Query(..., description="По проекту")
        ] = None,
        counterparty_id: Annotated[
            UUID | None, Query(..., description="По контрагенту")
        ] = None,
        status: Annotated[
            TicketStatus | None,
            Query(..., description="По статусу")
        ] = None,
        priority: Annotated[
            TicketPriority | None,
            Query(..., description="По приоритету")
        ] = None,
        # Дополнительные фильтры
        assigned_to: Annotated[
            UUID | None, Query(..., description="По исполнителю")
        ] = None,
        tags: Annotated[
            list[str] | None, Query(..., description="По тегам")
        ] = None,
        search: Annotated[
            str | None, Query(..., description="Запрос для полнотекстового поиска")
        ] = None,
) -> TicketFilter:
    """Зависимость для фильтрации тикетов в зависимости от роли пользователя"""

    # 1. Клиент может видеть только свои тикеты
    if current_user.role == UserRole.CUSTOMER:
        if reporter_id is not None and reporter_id != current_user.user_id:
            raise PermissionDeniedError("Customers can only see their tickets")

        reporter_id = current_user.user_id
        counterparty_id = None

    # 2. Администратор заказчика может видеть все тикеты своего контрагента
    elif current_user.role == UserRole.CUSTOMER_ADMIN:
        if counterparty_id is not None and counterparty_id != current_user.counterparty_id:
            raise PermissionDeniedError(
                "Customer admin can only see tickets belonging to its counterparty"
            )

        counterparty_id = current_user.counterparty_id

    return TicketFilter(
        reporter_id=reporter_id,
        created_by=created_by,
        project_id=project_id,
        counterparty_id=counterparty_id,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        tags=tags,
        search=search,
    )


TicketFiltersDep = Annotated[TicketFilter, Depends(get_ticket_filters)]
