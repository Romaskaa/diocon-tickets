from ..shared.schemas import Page
from .domain.entities import Project, ProjectMembership, ProjectStage
from .schemas import (
    ProjectDetailedResponse,
    ProjectMembershipResponse,
    ProjectResponse,
    ProjectStageResponse,
)


def map_membership_to_response(membership: ProjectMembership) -> ProjectMembershipResponse:
    return ProjectMembershipResponse(
        project_id=membership.project_id,
        project_role=membership.project_role,
        user_id=membership.user_id,
        created_by=membership.created_by,
        created_at=membership.created_at,
        is_active=not membership.is_deleted,
    )


def map_project_stage_to_response(stage: ProjectStage) -> ProjectStageResponse:
    return ProjectStageResponse(
        id=stage.project_id,
        created_at=stage.created_at,
        updated_at=stage.updated_at,
        project_id=stage.project_id,
        name=stage.name,
        order=stage.order,
        status=stage.status,
        planned_start=stage.planned_start,
        planned_end=stage.planned_end,
        started_at=stage.started_at,
        completed_at=stage.completed_at,
        responsible_id=stage.responsible_id,
        description=stage.description,
        completion_criteria=stage.completion_criteria,
        is_overdue=stage.is_overdue,
        planned_duration_days=stage.planned_duration_days,
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
        current_stage_id=project.current_stage_id,
        stages=[map_project_stage_to_response(stage) for stage in project.stages],
    )


def map_project_to_detailed_response(
        project: Project, memberships: Page[ProjectMembership],
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
        current_stage_id=project.current_stage_id,
        stages=[map_project_stage_to_response(stage) for stage in project.stages],
        memberships=memberships.to_response(map_membership_to_response),
    )
