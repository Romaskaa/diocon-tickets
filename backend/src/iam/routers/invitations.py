from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from ...shared.dependencies import PageParamsDep
from ...shared.domain.exceptions import NotFoundError
from ...shared.schemas import Page
from ..dependencies import (
    CurrentSupportUserDep,
    InvitationServiceDep,
    get_current_support_user,
    get_invitation_repo,
)
from ..domain.repos import InvitationRepository
from ..mappers import map_invitation_to_response
from ..schemas import InvitationCreate, InvitationResponse

router = APIRouter(
    prefix="/invitations",
    tags=["Приглашения"],
    dependencies=[Depends(get_current_support_user)]
)


@router.post(
    path="",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Отправка приглашения",
    description="Приглашения можно отправлять только с ролью `support` и выше"
)
async def send_invitation(
        current_user: CurrentSupportUserDep,
        data: InvitationCreate,
        background_tasks: BackgroundTasks,
        service: InvitationServiceDep,
) -> dict[str, str]:
    background_tasks.add_task(
        service.send_invitation,
        invited_by=current_user.user_id,
        email=data.email,
        assigned_role=data.assigned_role,
        counterparty_id=data.counterparty_id,
    )
    return {"message": "Приглашение будет отправлено в ближайшее время"}


@router.get(
    path="/{invitation_id}",
    status_code=status.HTTP_200_OK,
    response_model=InvitationResponse,
    summary="Получение информации и приглашении"
)
async def get_invitation(
        invitation_id: UUID, repository: InvitationRepository = Depends(get_invitation_repo)
) -> InvitationResponse:
    invitation = await repository.read(invitation_id)
    if invitation is None:
        raise NotFoundError(f"Invitation with ID {invitation_id} not found")
    return map_invitation_to_response(invitation)


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[InvitationResponse],
    summary="Получение всех приглашений",
)
async def get_invitations(
        params: PageParamsDep, repository: InvitationRepository = Depends(get_invitation_repo)
) -> Page[InvitationResponse]:
    page = await repository.paginate(params)
    return page.to_response(map_invitation_to_response)


@router.delete(
    path="/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отзыв приглашения",
    description="""\
    Отзывает ещё не принятое приглашение (с удалением на сервере).
    Применение: приглашение было отправлено по ошибке.
    """,
    responses={
        204: {"description": "Приглашение успешно удалено"},
        404: {"description": "Приглашение не найдено"}
    }
)
async def revoke_invitation(invitation_id: UUID, service: InvitationServiceDep) -> None:
    await service.revoke_invitation(invitation_id)
