from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query

from src.iam.dependencies import CurrentSubjectDep, UserRepoDep
from src.shared.dependencies import EventPublisherDep, PaginationDep, SessionDep
from src.shared.domain.exceptions import NotFoundError
from src.shared.schemas import Page

from .domain.repos import ProjectMembershipRepository, ProjectRepository
from .infra.repos import SqlMembershipRepository, SqlProjectRepository
from .mappers import map_project_to_response
from .schemas import ProjectResponse
from .services import ProjectMembershipService, ProjectService


def get_project_repo(session: SessionDep) -> SqlProjectRepository:
    return SqlProjectRepository(session)


def get_membership_repo(session: SessionDep) -> SqlMembershipRepository:
    return SqlMembershipRepository(session)


ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repo)]
MembershipRepoDep = Annotated[ProjectMembershipRepository, Depends(get_membership_repo)]


def get_project_service(
        session: SessionDep,
        project_repo: ProjectRepoDep,
        membership_repo: MembershipRepoDep,
        event_publisher: EventPublisherDep,
) -> ProjectService:
    return ProjectService(
        session=session,
        project_repo=project_repo,
        membership_repo=membership_repo,
        event_publisher=event_publisher,
    )


def get_project_membership_service(
        session: SessionDep,
        project_repo: ProjectRepoDep,
        user_repo: UserRepoDep,
        membership_repo: MembershipRepoDep,
        event_publisher: EventPublisherDep,
) -> ProjectMembershipService:
    return ProjectMembershipService(
        session=session,
        project_repo=project_repo,
        user_repo=user_repo,
        membership_repo=membership_repo,
        event_publisher=event_publisher,
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
ProjectMembershipServiceDep = Annotated[
    ProjectMembershipService, Depends(get_project_membership_service)
]


async def get_project_or_404(project_id: UUID, project_repo: ProjectRepoDep) -> ProjectResponse:
    project = await project_repo.read(project_id)
    if project is None:
        raise NotFoundError(f"Project with ID {project_id} not found")

    return map_project_to_response(project)


async def get_projects_page(
        pagination: PaginationDep, project_repo: ProjectRepoDep
) -> Page[ProjectResponse]:
    page = await project_repo.paginate(pagination)
    return page.to_response(map_project_to_response)


async def get_my_projects(
        current_subject: CurrentSubjectDep,
        pagination: PaginationDep,
        project_repo: ProjectRepoDep,
        owner_only: Annotated[
            bool, Query(description="Только те, где пользователь владелец")
        ] = False,
) -> Page[ProjectResponse]:
    page = await project_repo.get_by_user_membership(
        user_id=current_subject.id,
        pagination=pagination,
        owner_only=owner_only,
    )
    return page.to_response(map_project_to_response)


ProjectDep = Annotated[ProjectResponse, Depends(get_project_or_404)]
ProjectPageDep = Annotated[Page[ProjectResponse], Depends(get_projects_page)]
MyProjectsDep = Annotated[Page[ProjectResponse], Depends(get_my_projects)]
