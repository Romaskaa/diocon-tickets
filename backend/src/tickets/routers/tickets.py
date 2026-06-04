from typing import Annotated, Any

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status

from ...iam.dependencies import CurrentUserDep, get_current_user
from ...shared.dependencies import PageParamsDep
from ...shared.domain.exceptions import NotFoundError
from ...shared.schemas import Page
from ..dependencies import (
    CommentServiceDep,
    ReactionServiceDep,
    TicketFiltersDep,
    TicketRepoDep,
    TicketServiceDep,
)
from ..domain.vo import ReactionType
from ..infra.ai import predict_ticket_fields
from ..mappers import map_ticket_to_preview, map_ticket_to_response
from ..schemas import (
    CommentCreate,
    CommentEdit,
    CommentResponse,
    CommentWithReactionsResponse,
    PredictionResponse,
    ReactionResponse,
    TicketAssign,
    TicketCreate,
    TicketEdit,
    TicketPredict,
    TicketPreview,
    TicketResponse,
    TicketStatusChange,
)

router = APIRouter(prefix="/tickets", tags=["Тикеты"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=TicketResponse,
    summary="Создание нового тикета"
)
async def create_ticket(
        current_user: CurrentUserDep, data: TicketCreate, service: TicketServiceDep
) -> TicketResponse:
    return await service.create(
        data, created_by=current_user.user_id, created_by_role=current_user.role
    )


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=Page[TicketPreview],
    summary="Получение моих тикетов",
    description="Только те тикеты, где текущий пользователь записан как инициатор"
)
async def get_my_tickets(
        current_user: CurrentUserDep,
        params: PageParamsDep,
        repository: TicketRepoDep,
) -> Page[dict[str, Any]]:
    page = await repository.get_by_reporter(current_user.user_id, params)
    return page.to_response(map_ticket_to_preview)


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[TicketPreview],
    dependencies=[Depends(get_current_user)],
    summary="Фильтрация тикетов с пагинацией",
    description="Фильтрует тикеты учитывая роль пользователя",
    responses={
        200: {"description": "Фильтры успешно применены и получен результат"},
        403: {"description": "Недостаточно прав на указанную фильтрацию"}
    }
)
async def get_tickets(
        params: PageParamsDep,
        filters: TicketFiltersDep,
        repository: TicketRepoDep,
) -> Page[TicketPreview]:
    page = await repository.paginate(params, filters)
    return page.to_response(map_ticket_to_preview)


@router.get(
    path="/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    dependencies=[Depends(get_current_user)],
    summary="Получение тикета по его ID"
)
async def get_ticket(ticket_id: UUID, repository: TicketRepoDep) -> TicketResponse:
    ticket = await repository.read(ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket with ID {ticket_id} not found")
    return map_ticket_to_response(ticket)


@router.patch(
    path="/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    summary="Редактирование тикета",
    description="",
)
async def update_ticket(
        ticket_id: UUID,
        data: TicketEdit,
        current_user: CurrentUserDep,
        service: TicketServiceDep,
) -> TicketResponse:
    return await service.edit(ticket_id, data, edited_by=current_user.user_id)


@router.post(
    path="/{ticket_id}/assign",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    summary="Назначить тикет на пользователя",
    description="Назначает тикет на агента поддержки. Доступно только для сотрудников поддержки",
)
async def assign_ticket(
        ticket_id: UUID,
        data: TicketAssign,
        current_user: CurrentUserDep,
        service: TicketServiceDep,
) -> TicketResponse:
    return await service.assign_to(
        ticket_id=ticket_id,
        assignee_id=data.assignee_id,
        assigned_by=current_user.user_id,
        assigned_by_role=current_user.role,
    )


@router.patch(
    path="/{ticket_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    summary="Изменение статуса тикета",
    responses={
        200: {"description": "Статус успешно изменён"},
        403: {"description": "Недостаточно прав для изменения статуса"},
        404: {"description": "Тикет не найден"},
    }
)
async def change_ticket_status(
        ticket_id: UUID,
        data: TicketStatusChange,
        current_user: CurrentUserDep,
        service: TicketServiceDep,
) -> TicketResponse:
    return await service.change_status(
        ticket_id=ticket_id,
        new_status=data.status,
        changed_by=current_user.user_id,
        changed_by_role=current_user.role,
    )


@router.delete(
    path="/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    summary="Архивирование тикета",
    description="Soft-delete метод, не удаляет тикет фактически (добавляет в архив)",
)
async def delete_ticket(
        ticket_id: UUID, current_user: CurrentUserDep, service: TicketServiceDep
) -> TicketResponse:
    return await service.archive(
        ticket_id=ticket_id,
        archived_by=current_user.user_id,
        archived_by_role=current_user.role,
    )


@router.get(
    path="/{ticket_id}/comments",
    status_code=status.HTTP_200_OK,
    response_model=Page[CommentWithReactionsResponse],
    summary="Получение комментариев тикета"
)
async def get_ticket_comments(
        ticket_id: UUID,
        pagination: PageParamsDep,
        current_user: CurrentUserDep,
        service: CommentServiceDep,
        include_internal: Annotated[
            bool, Query(..., description="Видеть внутренние комментарии (только для поддержки)")
        ] = False,
) -> Page[CommentWithReactionsResponse]:
    return await service.get_comments(
        ticket_id=ticket_id,
        pagination=pagination,
        current_user=current_user,
        include_internal=include_internal,
    )


@router.get(
    path="/comments/{comment_id}/replies",
    status_code=status.HTTP_200_OK,
    response_model=Page[CommentWithReactionsResponse],
    summary="Получение ответов на комментарий"
)
async def get_comment_replies(
        comment_id: UUID,
        pagination: PageParamsDep,
        current_user: CurrentUserDep,
        service: CommentServiceDep,
        include_internal: Annotated[
            bool, Query(..., description="Видеть внутренние комментарии (только для поддержки)")
        ] = False,
) -> Page[CommentWithReactionsResponse]:
    return await service.get_comment_replies(
        comment_id=comment_id,
        pagination=pagination,
        current_user=current_user,
        include_internal=include_internal,
    )


@router.post(
    path="/{ticket_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
    summary="Оставить комментарий к тикету",
)
async def add_comment(
        ticket_id: UUID,
        data: CommentCreate,
        current_user: CurrentUserDep,
        service: CommentServiceDep,
) -> CommentResponse:
    return await service.add_comment(ticket_id, data, current_user)


@router.post(
    path="/{ticket_id}/comments/{comment_id}/replies",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
    summary="Ответить на комментарий"
)
async def add_comment_reply(
        ticket_id: UUID,
        comment_id: UUID,
        data: CommentCreate,
        current_user: CurrentUserDep,
        service: CommentServiceDep,
) -> CommentResponse:
    return await service.reply_to_comment(
        ticket_id=ticket_id,
        parent_comment_id=comment_id,
        data=data,
        current_user=current_user,
    )


@router.patch(
    path="/{ticket_id}/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    response_model=CommentResponse,
    summary="Редактирование комментария",
)
async def edit_comment(
        ticket_id: UUID,
        comment_id: UUID,
        data: CommentEdit,
        current_user: CurrentUserDep,
        service: CommentServiceDep,
) -> CommentResponse:
    return await service.edit_comment(
        ticket_id=ticket_id,
        comment_id=comment_id,
        data=data,
        edited_by=current_user.user_id
    )


@router.delete(
    path="/{ticket_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление комментария (Soft-delete)"
)
async def delete_comment(
        ticket_id: UUID,
        comment_id: UUID,
        current_user: CurrentUserDep,
        service: CommentServiceDep,
) -> None:
    return await service.delete_comment(
        ticket_id=ticket_id,
        comment_id=comment_id,
        deleted_by=current_user.user_id,
        deleted_by_role=current_user.role,
    )


@router.post(
    path="/comments/{comment_id}/reactions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Оставить/переключить реакцию",
    description="""\
    Реализует 3 сценария:

     - Создание новой реакции
     - Переключение между реакциями (реакция была создана, пользователь нажал на другую)
     - Удаление реакции (пользователь нажал на поставленную реакцию)
    """
)
async def toggle_reaction(
        comment_id: UUID,
        current_user: CurrentUserDep,
        service: ReactionServiceDep,
        reaction_type: Annotated[
            ReactionType, Body(..., embed=True, description="Реакция, которую нужно оставить")
        ],
) -> None:
    return await service.toggle(
        comment_id=comment_id, current_user=current_user, reaction_type=reaction_type
    )


@router.get(
    path="/comments/{comment_id}/reactions",
    status_code=status.HTTP_200_OK,
    response_model=ReactionResponse,
    summary="Получение реакции на комментарий"
)
async def get_comment_reactions(
        comment_id: UUID, current_user: CurrentUserDep, service: ReactionServiceDep
) -> ReactionResponse:
    return await service.get_reactions_for_comment(comment_id, current_user)


@router.post(
    path="/predict",
    status_code=status.HTTP_200_OK,
    response_model=PredictionResponse,
    summary="Определение приоритета и генерация тегов"
)
async def predict_for_ticket(data: TicketPredict) -> PredictionResponse:
    return await predict_ticket_fields(data)
