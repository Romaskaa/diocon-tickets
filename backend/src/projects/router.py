from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.iam.dependencies import CurrentSubjectDep, get_current_subject, require_role
from src.iam.domain.constants import SUPPORT_MANAGER_OR_ABOVE
from src.shared.schemas import Page

from .dependencies import (
    MyProjectsDep,
    ProjectDep,
    ProjectMembershipServiceDep,
    ProjectPageDep,
    ProjectServiceDep,
)
from .schemas import (
    KeyCheckResult,
    NewProjectStagesOrder,
    ProjectCreate,
    ProjectMembershipCreate,
    ProjectMembershipResponse,
    ProjectResponse,
    ProjectStageCreate,
    ProjectStagePlan,
    ProjectStageResponse,
    ProjectStageUpdate,
)
from .utils import generate_project_key

router = APIRouter(prefix="/projects", tags=["Проекты"])


@router.get(
    path="/key-suggestion",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, str],
    summary="Предлагает ключ проекта",
    description="Генерирует человекочитаемый ключ проекта, например - `CP`"
)
def get_key_suggestion(
        name: str = Query(..., description="Наименование проекта"),
) -> dict[str, str]:
    return {"key": generate_project_key(name)}


@router.get(
    path="/keys/{key}",
    status_code=status.HTTP_200_OK,
    response_model=KeyCheckResult,
    dependencies=[Depends(require_role(SUPPORT_MANAGER_OR_ABOVE))],
    summary="Проверяет свободен ли ключ"
)
async def check_project_key(key: str, service: ProjectServiceDep) -> KeyCheckResult:
    return await service.check_key(key)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
    summary="Создать новый проект",
    description="Проекты могут создавать только внутренние сотрудники",
    responses={
        201: {"description": "Проект успешно создан."},
        409: {"description": "Ключ уже занят (не удалось разрешить конфликт уникальности)."},
        403: {"description": "Недостаточно прав для создания проекта (недоступно для клиентов)."},
    },
)
async def create_project(
        current_subject: CurrentSubjectDep, data: ProjectCreate, service: ProjectServiceDep
) -> ProjectResponse:
    return await service.create(data, current_subject)


@router.get(
    path="/my",
    status_code=status.HTTP_200_OK,
    response_model=Page[ProjectResponse],
    summary="Получение моих проектов",
    description="""\
    Получение проектов пользователя в зависимости от параметра role:

     - `owner` - проекты, где пользователь является владельцем.
     - `member` - пользователь любой другой участник, кроме владельца.
     - `all` - любой участник (на важно какая роль).
    """,
)
async def get_my_projects(my_projects: MyProjectsDep) -> Page[ProjectResponse]:
    return my_projects


@router.get(
    path="/{project_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    dependencies=[Depends(get_current_subject)],
    summary="Получить проект",
)
async def get_project(project: ProjectDep) -> ProjectResponse:
    return project


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[ProjectResponse],
    dependencies=[Depends(require_role(SUPPORT_MANAGER_OR_ABOVE))],
    summary="Получить все проекты"
)
async def get_projects(page: ProjectPageDep) -> Page[ProjectResponse]:
    return page


@router.post(
    path="/{project_id}/memberships",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectMembershipResponse,
    summary="Добавить участника в проект"
)
async def create_project_membership(
        project_id: UUID,
        data: ProjectMembershipCreate,
        current_subject: CurrentSubjectDep,
        service: ProjectMembershipServiceDep,
) -> ProjectMembershipResponse:
    return await service.add_member(project_id, data, current_subject)


@router.delete(
    path="/{project_id}/memberships/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить участника из проекта"
)
async def delete_project_membership(
        project_id: UUID,
        user_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectMembershipServiceDep,
) -> None:
    return await service.remove_member(project_id, user_id, current_subject)


@router.post(
    path="/{project_id}/stages",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
    summary="Создать этап проекта"
)
async def create_project_stage(
        project_id: UUID,
        data: ProjectStageCreate,
        current_subject: CurrentSubjectDep,
        service: ProjectMembershipServiceDep,
) -> ProjectResponse:
    return await service.add_member(project_id, data, current_subject)


@router.patch(
    path="/{project_id}/stages/{stage_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectStageResponse,
    summary="Обновить этап проекта",
)
async def update_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        data: ProjectStageUpdate,
        service: ProjectServiceDep,
) -> ProjectStageResponse:
    return await service.edit_stage(
        project_id=project_id,
        stage_id=stage_id,
        data=data,
        current_subject=current_subject,
    )


@router.patch(
    path="/{project_id}/stages/order",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Изменить порядок проведения этапов",
)
async def reorder_project_stages(
        project_id: UUID,
        new_order: NewProjectStagesOrder,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.reorder_stages(
        project_id=project_id,
        new_order=new_order,
        current_subject=current_subject,
    )


@router.delete(
    path="/{project_id}/stages/{stage_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Удалить этап из проекта"
)
async def delete_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.remove_stage(
        project_id=project_id,
        stage_id=stage_id,
        current_subject=current_subject,
    )


@router.post(
    path="/{project_id}/stages/{stage_id}/start",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Начать этап проекта"
)
async def start_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.start_stage(
        project_id=project_id, stage_id=stage_id, current_subject=current_subject
    )


@router.post(
    path="/{project_id}/stages/{stage_id}/complete",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Завершить этап проекта"
)
async def complete_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.complete_stage(
        project_id=project_id, stage_id=stage_id, current_subject=current_subject
    )


@router.post(
    path="/{project_id}/stages/{stage_id}/skip",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Пропустить этап проекта"
)
async def skip_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.complete_stage(
        project_id=project_id, stage_id=stage_id, current_subject=current_subject,
    )


@router.patch(
    path="/{project_id}/stages/{stage_id}/schedule",
    status_code=status.HTTP_200_OK,
    response_model=ProjectStageResponse,
    summary="Запланировать проведение этапа",
)
async def schedule_project_stage(
        project_id: UUID,
        stage_id: UUID,
        data: ProjectStagePlan,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectStageResponse:
    return await service.schedule_stage(
        project_id=project_id,
        stage_id=stage_id,
        data=data,
        current_subject=current_subject,
    )
