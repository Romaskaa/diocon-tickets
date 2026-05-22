from typing import Annotated

from fastapi import Depends

from ..iam.dependencies import UserRepoDep
from ..projects.dependencies import ProjectAccessServiceDep, ProjectRepoDep
from ..shared.dependencies import SessionDep
from ..tickets.dependencies import TicketRepoDep
from .domain.repos import TaskRepository
from .infra.repos import SqlTaskRepository
from .services import TaskService


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
) -> TaskService:
    return TaskService(
        session=session,
        task_repo=task_repo,
        ticket_repo=ticket_repo,
        user_repo=user_repo,
        project_repo=project_repo,
        project_access_service=project_access_service,
    )


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
