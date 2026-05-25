from typing import Annotated

from fastapi import Depends, Query

from ..iam.dependencies import UserRepoDep
from ..projects.dependencies import ProjectAccessServiceDep, ProjectRepoDep
from ..shared.dependencies import EventPublisherDep, SessionDep
from ..tickets.dependencies import TicketRepoDep
from ..tickets.domain.vo import Priority
from .domain.repos import TaskRepository
from .infra.repos import SqlTaskRepository
from .schemas import KanbanFilters
from .services import TaskBoardService, TaskService


def get_task_repo(session: SessionDep) -> SqlTaskRepository:
    return SqlTaskRepository(session)


TaskRepoDep = Annotated[TaskRepository, Depends(get_task_repo)]


def get_task_service(
        session: SessionDep,
        task_repo: TaskRepoDep,
        ticket_repo: TicketRepoDep,
        user_repo: UserRepoDep,
        project_repo: ProjectRepoDep,
        project_access_service: ProjectAccessServiceDep,
        event_publisher: EventPublisherDep,
) -> TaskService:
    return TaskService(
        session=session,
        task_repo=task_repo,
        ticket_repo=ticket_repo,
        user_repo=user_repo,
        project_repo=project_repo,
        project_access_service=project_access_service,
        event_publisher=event_publisher,
    )


def get_task_board_service(
        task_repo: TaskRepoDep, project_access_service: ProjectAccessServiceDep
) -> TaskBoardService:
    return TaskBoardService(task_repo=task_repo, project_access_service=project_access_service)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
TaskBoardServiceDep = Annotated[TaskBoardService, Depends(get_task_board_service)]


def get_kanban_filters(
        priorities: Annotated[
            list[Priority] | None, Query(..., description="По приоритету")
        ] = None,
        overdue_only: Annotated[bool, Query(..., description="Только просроченные")] = False,
) -> KanbanFilters:
    return KanbanFilters(priorities=priorities, overdue_only=overdue_only)


KanbanFiltersDep = Annotated[KanbanFilters, Depends(get_kanban_filters)]
