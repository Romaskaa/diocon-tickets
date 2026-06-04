from typing import Annotated, Any, Literal

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from ...iam.dependencies import CurrentSupportUserDep, CurrentUserDep, require_role
from ...iam.domain.constants import SUPPORT_TEAM
from ...shared.dependencies import PageParamsDep
from ...shared.domain.exceptions import NotFoundError
from ...shared.schemas import Page
from ..dependencies import ProjectRepoDep, ProjectServiceDep
from ..domain.services import generate_project_key
from ..mappers import map_project_to_response
from ..schemas import KeyCheckResponse, MembersAdd, ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Проекты"])


@router.get(
    path="/key-suggestion",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, str],
    summary="Предлагает ключ для проекта",
    description="Генерирует читабельный ключ для проекта, например - 'CP'"
)
def get_key_suggestion(
        name: str = Query(..., description="Наименование проекта"),
) -> dict[str, str]:
    return {"key": generate_project_key(name)}


@router.get(
    path="/keys/{key}",
    status_code=status.HTTP_200_OK,
    response_model=KeyCheckResponse,
    summary="Проверка доступности ключа"
)
async def check_project_key(key: str, service: ProjectServiceDep) -> KeyCheckResponse:
    return await service.check_key(key)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
    responses={
        201: {"description": "Проект успешно создан"},
        409: {"description": "Ключ уже занят (не получилось разрешить конфликт уникальности)"},
    },
    summary="Создание проекта",
    description="Проекты могут создавать только пользователи с ролью `support` и выше",
)
async def create_project(
        current_user: CurrentSupportUserDep, data: ProjectCreate, service: ProjectServiceDep
) -> ProjectResponse:
    return await service.create(data, created_by=current_user.user_id)


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
async def get_my_projects(
        current_user: CurrentUserDep,
        pagination: PageParamsDep,
        repository: ProjectRepoDep,
        role: Annotated[
            Literal["owner", "member", "all"],
            Query(..., description="Роль пользователя в проекте")
        ] = "all",
) -> Page[dict[str, Any]]:
    page = await repository.get_by_user_membership(
        user_id=current_user.user_id, pagination=pagination, role=role
    )
    return page.to_response(map_project_to_response)


@router.get(
    path="/{project_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Получение проекта"
)
async def get_project(project_id: UUID, repository: ProjectRepoDep) -> ProjectResponse:
    project = await repository.read(project_id)
    if project is None:
        raise NotFoundError(f"Project with ID {project_id} not found")
    return map_project_to_response(project)


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[ProjectResponse],
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Получение всех проектов"
)
async def get_projects(params: PageParamsDep, repository: ProjectRepoDep) -> Page[dict[str, Any]]:
    page = await repository.paginate(params)
    return page.to_response(map_project_to_response)


@router.post(
    path="/{project_id}/memberships",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
    summary="Добавление участников в проект"
)
async def add_members_to_project(
        project_id: Annotated[UUID, Path(..., description="ID проекта")],
        data: MembersAdd,
        current_user: CurrentUserDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.add_members(
        project_id, data, added_by=current_user.user_id, added_by_role=current_user.role
    )
