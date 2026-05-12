from ..shared.schemas import Page
from .domain.entities import Membership, Project
from .schemas import MembershipResponse, ProjectDetailedResponse, ProjectResponse


def map_membership_to_response(membership: Membership) -> MembershipResponse:
    return MembershipResponse(
        project_role=membership.project_role,
        user_id=membership.user_id,
        added_at=membership.added_at,
        added_by=membership.added_by,
        is_active=not membership.is_deleted,
    )


def map_project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        name=project.name,
        key=f"{project.key}",
        description=project.description,
        owner_id=project.owner_id,
        counterparty_id=project.counterparty_id,
        created_by=project.created_by,
        status=project.status,
    )


def map_project_to_detailed_response(
        project: Project, memberships: Page[Membership],
) -> ProjectDetailedResponse:
    return ProjectDetailedResponse(
        id=project.id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        name=project.name,
        key=f"{project.key}",
        description=project.description,
        owner_id=project.owner_id,
        counterparty_id=project.counterparty_id,
        created_by=project.created_by,
        status=project.status,
        memberships=memberships.to_response(map_membership_to_response),
    )
