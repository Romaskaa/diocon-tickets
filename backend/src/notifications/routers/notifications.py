from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Query, status

from ...iam.dependencies import CurrentUserDep
from ...shared.dependencies import PageParamsDep
from ...shared.schemas import Page
from ..dependencies import NotificationRepoDep, NotificationServiceDep
from ..mappers import map_notification_to_response
from ..schemas import NotificationResponse, UnreadCountOut

router = APIRouter(prefix="/notifications", tags=["Уведомления"])


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[NotificationResponse],
    summary="Получение моих уведомлений",
)
async def get_my_notifications(
        current_user: CurrentUserDep,
        repository: NotificationRepoDep,
        pagination: PageParamsDep,
        unread_only: Annotated[
            bool, Query(..., description="Учитывать только непрочитанные")
        ] = False,
) -> Page[NotificationResponse]:
    page = await repository.get_by_user(current_user.user_id, pagination, unread_only)
    return page.to_response(map_notification_to_response)


@router.get(
    path="/unread-count",
    status_code=status.HTTP_200_OK,
    response_model=UnreadCountOut,
    summary="Получение количества непрочитанных уведомлений",
)
async def get_unread_count(
        current_user: CurrentUserDep, repository: NotificationRepoDep
) -> UnreadCountOut:
    return {"unread_count": await repository.get_unread_count(current_user.user_id)}


@router.patch(
    path="/{notification_id}/read",
    status_code=status.HTTP_200_OK,
    response_model=NotificationResponse,
    summary="Пометить уведомление как прочитанное",
)
async def mark_as_read(
        notification_id: UUID,
        current_user: CurrentUserDep,
        service: NotificationServiceDep,
) -> NotificationResponse:
    return await service.mark_as_read(notification_id, read_by=current_user.user_id)
