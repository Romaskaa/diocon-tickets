from typing import Annotated

from datetime import datetime
from uuid import UUID

from fastapi import Depends, Query

from ..core.database import session_factory
from ..crm.dependencies import CounterpartyRepoDep
from ..crm.domain.entities import Counterparty
from ..crm.infra.repos import SqlCounterpartyRepository
from ..iam.dependencies import UserRepoDep
from ..iam.domain.entities import User
from ..iam.infra.repos import SqlUserRepository
from ..projects.dependencies import ProjectMemberRepoDep, ProjectAccessServiceDep, ProjectRepoDep
from ..projects.domain.entities import Project
from ..projects.infra.repos import SqlProjectRepository
from ..shared.dependencies import EventPublisherDep, SessionDep
from .domain.repos import CommentRepository, ReactionRepository, TicketFilters, TicketRepository
from .domain.services import TicketScopeService
from .domain.vo import Priority, TicketStatus, TicketType
from .infra.repos import SqlCommentRepository, SqlReactionRepository, SqlTicketRepository
from .loaders import TicketDataLoader
from .services import CommentService, ReactionService, TicketService, TicketViewService


def get_ticket_repo(session: SessionDep) -> SqlTicketRepository:
    return SqlTicketRepository(session)


def get_comment_repo(session: SessionDep) -> SqlCommentRepository:
    return SqlCommentRepository(session)


def get_reaction_repo(session: SessionDep) -> SqlReactionRepository:
    return SqlReactionRepository(session)


TicketRepoDep = Annotated[TicketRepository, Depends(get_ticket_repo)]
CommentRepoDep = Annotated[CommentRepository, Depends(get_comment_repo)]
ReactionRepoDep = Annotated[ReactionRepository, Depends(get_reaction_repo)]


def get_ticket_service(
        session: SessionDep,
        counterparty_repo: CounterpartyRepoDep,
        ticket_repo: TicketRepoDep,
        project_repo: ProjectRepoDep,
        project_access_service: ProjectAccessServiceDep,
        user_repo: UserRepoDep,
        event_publisher: EventPublisherDep
) -> TicketService:
    return TicketService(
        session=session,
        counterparty_repo=counterparty_repo,
        ticket_repo=ticket_repo,
        project_repo=project_repo,
        project_access_service=project_access_service,
        user_repo=user_repo,
        event_publisher=event_publisher
    )


# Функции для пакетной загрузки данных
async def fetch_users(user_ids: list[UUID]) -> list[User]:
    async with session_factory() as session:
        user_repo = SqlUserRepository(session)
        return await user_repo.get_by_ids(user_ids)


async def fetch_counterparties(counterparty_ids: list[UUID]) -> list[Counterparty]:
    async with session_factory() as session:
        counterparty_repo = SqlCounterpartyRepository(session)
        return await counterparty_repo.get_by_ids(counterparty_ids)


async def fetch_projects(project_ids: list[UUID]) -> list[Project]:
    async with session_factory() as session:
        project_repo = SqlProjectRepository(session)
        return await project_repo.get_by_ids(project_ids)


def get_ticket_data_loader() -> TicketDataLoader:
    return TicketDataLoader(
        users_fetcher=fetch_users,
        counterparties_fetcher=fetch_counterparties,
        projects_fetcher=fetch_projects,
    )


def get_ticket_scope_service(membership_repo: ProjectMemberRepoDep) -> TicketScopeService:
    return TicketScopeService(project_membership_repo=membership_repo)


def get_ticket_view_service(
        ticket_repo: TicketRepoDep,
        ticket_scope_service: TicketScopeService = Depends(get_ticket_scope_service),
        ticket_data_loader: TicketDataLoader = Depends(get_ticket_data_loader)
) -> TicketViewService:
    return TicketViewService(
        ticket_repo=ticket_repo,
        ticket_scope_service=ticket_scope_service,
        ticket_data_loader=ticket_data_loader,
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


TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]
TicketViewServiceDep = Annotated[TicketViewService, Depends(get_ticket_view_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
ReactionServiceDep = Annotated[ReactionService, Depends(get_reaction_service)]


def get_ticket_filters(
        status: Annotated[
            TicketStatus | None, Query(..., description="По статусу")
        ] = None,
        priority: Annotated[
            Priority | None, Query(..., description="По приоритету")
        ] = None,
        ticket_type: Annotated[
            TicketType | None, Query(..., description="По виду заявки")
        ] = None,
        tags: Annotated[
            list[str] | None, Query(..., max_length=10, description="По тегам")
        ] = None,
        query: Annotated[str | None, Query(..., description="Поисковый запрос")] = None,
        created_after: Annotated[
            datetime | None, Query(..., description="Создан после")
        ] = None,
        created_before: Annotated[
            datetime | None, Query(..., description="Создан до")
        ] = None,
) -> TicketFilters:
    return TicketFilters(
        status=status,
        priority=priority,
        type=ticket_type,
        tags=tags,
        query=query,
        created_after=created_after,
        created_before=created_before,
    )


TicketFiltersDep = Annotated[TicketFilters, Depends(get_ticket_filters)]
