from uuid import UUID
from io import BytesIO

from fastapi import APIRouter, Depends, Query, status

from src.iam.dependencies import CurrentSubjectDep, get_current_subject, require_role
from src.iam.domain.constants import SUPPORT_MANAGER_OR_ABOVE
from src.shared.schemas import Page
from fastapi.responses import StreamingResponse

from .dependencies import (
    MyProjectsDep,
    ProjectDep,
    ProjectMemberServiceDep,
    ProjectServiceDep,
    ProjectsPageDep,
    ProjectStageExportServiceDep,
)
from .domain.services import generate_project_key
from .schemas import (
    KeyCheckResult,
    NewProjectStagesOrder,
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectStageCreate,
    ProjectStagePlan,
    ProjectStageResponse,
    ProjectStageUpdate,
)
from .exporters import (
    export_project_stages_to_excel,
    export_project_stages_to_pdf,
    export_project_stages_to_word,
)

router = APIRouter(prefix="/projects", tags=["Проекты"])


def _export_response(
        content: bytes,
        filename: str,
        media_type: str,
) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    path="/key-suggestion",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, str],
    summary="Предлагает ключ проекта",
    description="Генерирует человекочитаемый ключ проекта, например - `PRJ`"
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
    summary="Мои проекты",
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
    summary="Пагинация проектов"
)
async def get_projects(page: ProjectsPageDep) -> Page[ProjectResponse]:
    return page


@router.post(
    path="/{project_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectMemberResponse,
    summary="Добавить участника в проект"
)
async def create_project_member(
        project_id: UUID,
        data: ProjectMemberCreate,
        current_subject: CurrentSubjectDep,
        service: ProjectMemberServiceDep,
) -> ProjectMemberResponse:
    return await service.add_member(project_id, data, current_subject)


@router.delete(
    path="/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить участника из проекта"
)
async def delete_project_membership(
        project_id: UUID,
        user_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectMemberServiceDep,
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
        service: ProjectMemberServiceDep,
) -> ProjectResponse:
    return await service.add_member(project_id, data, current_subject)


@router.get(
    path='/{project_id}/stages/export/excel',
    status_code=status.HTTP_200_OK,
    summary="Экспортировать этапы проекта в Excel",
)
async def export_project_stages_excel(
    project_id: UUID,
    current_subject: CurrentSubjectDep,
    service: ProjectStageExportServiceDep,
) -> StreamingResponse:
    report = await service.build_report(
        project_id=project_id,
        current_subject=current_subject,
    )

    return _export_response(
        content=export_project_stages_to_excel(report),
        filename=f"project-stages-{report.project_key}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get(
    path="/{project_id}/stages/export/pdf",
    status_code=status.HTTP_200_OK,
    summary="Экспортировать этапы проекта в PDF",
)
async def export_project_stages_pdf(
    project_id: UUID,
    current_subject: CurrentSubjectDep,
    service: ProjectStageExportServiceDep,
) -> StreamingResponse:
    report = await service.build_report(
        project_id=project_id,
        current_subject=current_subject,
    )

    return _export_response(
        content=export_project_stages_to_pdf(report),
        filename=f"project-stages-{report.project_key}.pdf",
        media_type="application/pdf",
    )


@router.get(
    path="/{project_id}/stages/export/word",
    status_code=status.HTTP_200_OK,
    summary="Экспортировать этапы проекта в Word",
)
async def export_project_stages_word(
    project_id: UUID,
    current_subject: CurrentSubjectDep,
    service: ProjectStageExportServiceDep,
) -> StreamingResponse:
    report = await service.build_report(
        project_id=project_id,
        current_subject=current_subject,
    )

    return _export_response(
        content=export_project_stages_to_word(report),
        filename=f"project-stages-{report.project_key}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


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
