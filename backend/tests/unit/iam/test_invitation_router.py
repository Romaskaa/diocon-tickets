from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks

from src.iam.domain.services import invite_support
from src.iam.domain.vo import UserRole
from src.iam.routers.invitations import (
    get_invitation,
    get_invitations,
    revoke_invitation,
    send_invitation,
)
from src.iam.schemas import CurrentUser, InvitationCreate
from src.shared.domain.exceptions import NotFoundError
from src.shared.schemas import Pagination

EXPECTED_INVITATIONS_COUNT = 2


@pytest.fixture
def current_support_user():
    return CurrentUser(
        user_id=uuid4(),
        email="support@example.com",
        role=UserRole.SUPPORT_AGENT,
    )


class TestInvitationRouter:
    @pytest.mark.asyncio
    async def test_send_invitation_adds_background_task(self, current_support_user):
        """
        Проверяем POST-handler отправки приглашения: он нужен, чтобы API быстро
        вернул ответ клиенту, а реальную отправку письма положил в BackgroundTasks.
        Данные: support-пользователь и запрос на приглашение support-пользователя.
        """
        service = AsyncMock()
        background_tasks = BackgroundTasks()
        data = InvitationCreate(
            email="invitee@example.com",
            assigned_role=UserRole.SUPPORT_AGENT,
        )

        response = await send_invitation(
            current_user=current_support_user,
            data=data,
            background_tasks=background_tasks,
            service=service,
        )

        assert response == {
            "message": "Приглашение будет отправлено в ближайшее время",
        }
        assert len(background_tasks.tasks) == 1

        task = background_tasks.tasks[0]
        assert task.func == service.send_invitation
        assert task.kwargs == {
            "invited_by": current_support_user.user_id,
            "email": data.email,
            "assigned_role": data.assigned_role,
            "counterparty_id": data.counterparty_id,
        }

    @pytest.mark.asyncio
    async def test_get_invitation_returns_response(self, fake_invitation_repo):
        """
        Проверяем GET-handler приглашения по id: он нужен, чтобы роутер читал
        приглашение из репозитория и отдавал наружу response-схему.
        Данные: одно support-приглашение в in-memory репозитории.
        """
        invitation = invite_support(
            invited_by=uuid4(),
            email="invitee@example.com",
            assigned_role=UserRole.SUPPORT_AGENT,
        )
        await fake_invitation_repo.create(invitation)

        response = await get_invitation(invitation.id, repository=fake_invitation_repo)

        assert response.id == invitation.id
        assert response.email == invitation.email
        assert response.assigned_role == invitation.assigned_role
        assert response.is_used == invitation.is_used

    @pytest.mark.asyncio
    async def test_get_invitation_raises_not_found(self, fake_invitation_repo):
        """
        Проверяем GET-handler приглашения по id: он нужен, чтобы отсутствующее
        приглашение превращалось в понятную NotFoundError.
        Данные: случайный id, которого нет в in-memory репозитории.
        """
        invitation_id = uuid4()

        with pytest.raises(NotFoundError, match=f"Invitation with ID {invitation_id} not found"):
            await get_invitation(invitation_id, repository=fake_invitation_repo)

    @pytest.mark.asyncio
    async def test_get_invitations_returns_page(self, fake_invitation_repo):
        """
        Проверяем list-handler приглашений: он нужен, чтобы роутер возвращал
        страницу response-объектов и сохранял данные пагинации.
        Данные: два support-приглашения в in-memory репозитории.
        """
        first_invitation = invite_support(
            invited_by=uuid4(),
            email="first@example.com",
            assigned_role=UserRole.SUPPORT_AGENT,
        )
        second_invitation = invite_support(
            invited_by=uuid4(),
            email="second@example.com",
            assigned_role=UserRole.SUPPORT_MANAGER,
        )
        await fake_invitation_repo.create(first_invitation)
        await fake_invitation_repo.create(second_invitation)

        page = await get_invitations(
            params=Pagination(page=1, size=10),
            repository=fake_invitation_repo,
        )

        assert page.total_items == EXPECTED_INVITATIONS_COUNT
        assert {item.id for item in page.items} == {
            first_invitation.id,
            second_invitation.id,
        }

    @pytest.mark.asyncio
    async def test_revoke_invitation_calls_service(self):
        """
        Проверяем DELETE-handler приглашения: он нужен, чтобы роутер делегировал
        отзыв приглашения сервису и не дублировал бизнес-логику.
        Данные: случайный id приглашения и async service double.
        """
        invitation_id = uuid4()
        service = AsyncMock()

        await revoke_invitation(invitation_id, service=service)

        service.revoke_invitation.assert_awaited_once_with(invitation_id)
