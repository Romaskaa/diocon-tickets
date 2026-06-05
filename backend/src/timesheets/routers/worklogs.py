from uuid import UUID

from fastapi import APIRouter, status

from ...iam.dependencies import CurrentUserDep
from ..dependencies import WorklogServiceDep
from ..schemas import WorklogCreate, WorklogEdit, WorklogResponse

router = APIRouter(
    prefix="/worklogs", tags=["Журнал проделанных работ", "🕓 Учёт рабочего времени"]
)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=WorklogResponse,
    summary="Записать потраченное время в журнал"
)
async def create_worklog(
        data: WorklogCreate, current_user: CurrentUserDep, service: WorklogServiceDep
) -> WorklogResponse:
    return await service.log_time(data=data, current_user=current_user)


@router.patch(
    path="/{worklog_id}",
    status_code=status.HTTP_200_OK,
    response_model=WorklogResponse,
    summary="Редактировать лог",
)
async def update_worklog(
        worklog_id: UUID,
        data: WorklogEdit,
        current_user: CurrentUserDep,
        service: WorklogServiceDep
) -> WorklogResponse:
    return await service.edit(worklog_id=worklog_id, data=data, current_user=current_user)


@router.get(
    path="/{worklog_id}",
    status_code=status.HTTP_200_OK,
    response_model=...,
    summary="Получить запись о потраченном времени"
)
async def get_worklog(): ...
