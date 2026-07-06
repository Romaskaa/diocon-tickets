from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query

from src.activity_logs.dependencies import ActivityLogRecorderDep
from src.core.database import session_factory
from src.crm.dependencies import CounterpartyRepoDep
from src.crm.domain.entities import Counterparty
from src.crm.infra.repos import SqlCounterpartyRepository
from src.iam.dependencies import UserRepoDep
from src.iam.domain.entities import User
from src.iam.infra.repos import SqlUserRepository
from src.projects.dependencies import ProjectMemberRepoDep, ProjectRepoDep
from src.projects.domain.entities import Project
from src.projects.infra.repos import SqlProjectRepository
from src.shared.dependencies import (
    EventPublisherDep,
    PaginationDep,
    SessionDep,
    TimeRangeFiltersDep,
)
from src.shared.schemas import Page

from ..iam.domain.authz import Subject
from .domain.authz import TicketAuthZService
from .domain.dtos import TicketFilters
from .domain.repos import CommentRepository, ReactionRepository, TicketRepository
from .domain.vo import Priority, TicketStatus, TicketType
from .infra.repos import SqlCommentRepository, SqlReactionRepository, SqlTicketRepository
from .loaders import TicketReferenceLoader
from .schemas import TicketViewResponse
from .services import CommentService, ReactionService, TicketQueryService, TicketService


def get_ticket_repo(session: SessionDep) -> SqlTicketRepository:
    return SqlTicketRepository(session)


def get_comment_repo(session: SessionDep) -> SqlCommentRepository:
    return SqlCommentRepository(session)


def get_reaction_repo(session: SessionDep) -> SqlReactionRepository:
    return SqlReactionRepository(session)


TicketRepoDep = Annotated[TicketRepository, Depends(get_ticket_repo)]
CommentRepoDep = Annotated[CommentRepository, Depends(get_comment_repo)]
ReactionRepoDep = Annotated[ReactionRepository, Depends(get_reaction_repo)]


def get_ticket_authz_service(member_repo: ProjectMemberRepoDep) -> TicketAuthZService:
    return TicketAuthZService(member_repo)


TicketAuthZServiceDep = Annotated[TicketAuthZService, Depends(get_ticket_authz_service)]


def get_ticket_service(
        session: SessionDep,
        counterparty_repo: CounterpartyRepoDep,
        ticket_repo: TicketRepoDep,
        project_repo: ProjectRepoDep,
        user_repo: UserRepoDep,
        ticket_authz_service: TicketAuthZServiceDep,
        activity_log_recorder: ActivityLogRecorderDep,
        event_publisher: EventPublisherDep
) -> TicketService:
    return TicketService(
        uow=session,
        counterparty_repo=counterparty_repo,
        ticket_repo=ticket_repo,
        project_repo=project_repo,
        user_repo=user_repo,
        ticket_authz_service=ticket_authz_service,
        activity_log_recorder=activity_log_recorder,
        event_publisher=event_publisher
    )


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


def get_ticket_reference_loader() -> TicketReferenceLoader:
    return TicketReferenceLoader(
        users_fetcher=fetch_users,
        counterparties_fetcher=fetch_counterparties,
        projects_fetcher=fetch_projects,
    )


def get_ticket_query_service(
        ticket_repo: TicketRepoDep,
        reference_loader: TicketReferenceLoader = Depends(get_ticket_reference_loader)
) -> TicketQueryService:
    return TicketQueryService(ticket_repo=ticket_repo, reference_loader=reference_loader)


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
TicketQueryServiceDep = Annotated[TicketQueryService, Depends(get_ticket_query_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
ReactionServiceDep = Annotated[ReactionService, Depends(get_reaction_service)]


def get_ticket_filters(
        time_range: TimeRangeFiltersDep,
        statuses: Annotated[
            list[TicketStatus] | None, Query(max_length=5, description="По статусу")
        ] = None,
        priorities: Annotated[
            list[Priority] | None, Query(max_length=5, description="По приоритету")
        ] = None,
        ticket_type: Annotated[
            TicketType | None, Query(description="По виду заявки")
        ] = None,
        tags: Annotated[
            list[str] | None, Query(max_length=10, description="По тегам")
        ] = None,
        q: Annotated[str | None, Query(description="Поисковый запрос")] = None,
) -> TicketFilters:
    return TicketFilters(
        search_query=q,
        counterparty_id=...,
        project_ids=...,
        statuses=statuses,
        priorities=priorities,
        type=ticket_type,
        tags=tags,
        actors=...,
        time_range=time_range,
    )


TicketFiltersDep = Annotated[TicketFilters, Depends(get_ticket_filters)]


async def paginate_tickets(
        pagination: PaginationDep, filters: TicketFilters, ticket_repo: TicketRepoDep
) -> Page[TicketViewResponse]: ...
