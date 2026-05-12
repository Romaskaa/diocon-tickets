from typing import Annotated

from fastapi import Depends

from ..shared.dependencies import EventPublisherDep, SessionDep
from .domain.repos import MembershipRepository, ProjectRepository
from .domain.services import ProjectAccessService
from .infra.repos import SqlMembershipRepository, SqlProjectRepository
from .services import ProjectService


def get_project_repo(session: SessionDep) -> SqlProjectRepository:
    return SqlProjectRepository(session)


def get_membership_repo(session: SessionDep) -> SqlMembershipRepository:
    return SqlMembershipRepository(session)


ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repo)]
MembershipRepoDep = Annotated[MembershipRepository, Depends(get_membership_repo)]


def get_project_access_service(membership_repo: MembershipRepoDep) -> ProjectAccessService:
    return ProjectAccessService(membership_repo)


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


ProjectAccessServiceDep = Annotated[ProjectAccessService, Depends(get_project_access_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
