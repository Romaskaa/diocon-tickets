from uuid import UUID

from fastapi import APIRouter, status

from ..iam.dependencies import CurrentUserDep
from ..shared.dependencies import PaginationDep
from .dependencies import KanbanFiltersDep, TaskBoardServiceDep, TaskServiceDep
from .schemas import (
    AssigneeId,
    KanbanBoard,
    KanbanContextType,
    NewStatus,
    ReviewerId,
    TaskCreate,
    TaskEdit,
    TaskResponse,
    TaskReview,
)

router = APIRouter(prefix="/tasks", tags=["Задания сотрудникам"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskResponse,
    summary="Создать задачу"
)
async def create_task(
        data: TaskCreate, current_user: CurrentUserDep, service: TaskServiceDep
) -> TaskResponse:
    return await service.create(data, current_user)


@router.patch(
    path="/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Редактировать задачу"
)
async def edit_task(
        task_id: UUID, data: TaskEdit, current_user: CurrentUserDep, service: TaskServiceDep
) -> TaskResponse:
    return await service.edit(task_id, data, current_user)


@router.post(
    path="/{task_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Сменить статус"
)
async def move_task_status(
        task_id: UUID, new_status: NewStatus, current_user: CurrentUserDep, service: TaskServiceDep
) -> TaskResponse:
    return await service.change_status(task_id, new_status, current_user)


@router.post(
    path="/{task_id}/assign",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Назначить исполнителя"
)
async def assign_task(
        task_id: UUID,
        assignee_id: AssigneeId,
        current_user: CurrentUserDep,
        service: TaskServiceDep,
) -> TaskResponse:
    return await service.assign_to(task_id, assignee_id, current_user)


@router.post(
    path="/{task_id}/request-review",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Запросить ревью"
)
async def request_task_review(
        task_id: UUID,
        reviewer_id: ReviewerId,
        current_user: CurrentUserDep,
        service: TaskServiceDep,
) -> TaskResponse:
    return await service.request_review(task_id, reviewer_id, current_user)


@router.post(
    path="/{task_id}/review",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Провести ревью",
)
async def review_task(
        task_id: UUID, data: TaskReview, current_user: CurrentUserDep, service: TaskServiceDep
) -> TaskResponse:
    return await service.review(task_id, data, current_user)


@router.delete(
    path="/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Архивировать задачу"
)
async def archive_task(
        task_id: UUID, current_user: CurrentUserDep, service: TaskServiceDep
) -> TaskResponse:
    return await service.archive(task_id, current_user)


@router.post(
    path="/kanban",
    status_code=status.HTTP_200_OK,
    response_model=KanbanBoard,
    summary="Получить Kanban доску"
)
async def get_kanban_board(
        context: KanbanContextType,
        pagination: PaginationDep,
        filters: KanbanFiltersDep,
        current_user: CurrentUserDep,
        service: TaskBoardServiceDep,
) -> KanbanBoard:
    return await service.get_kanban_board(
        pagination=pagination,
        context=context,
        filters=filters,
        current_user=current_user,
    )
