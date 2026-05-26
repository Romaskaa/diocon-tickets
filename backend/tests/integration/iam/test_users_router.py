from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.crm.domain.vo import CounterpartyType
from src.crm.infra.models import CounterpartyOrm
from src.iam.dependencies import get_current_user, get_user_repo
from src.iam.domain.services import create_customer, create_support
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.iam.routers.users import get_me, get_supports, get_user, get_users
from src.iam.schemas import CurrentUser
from src.shared.domain.exceptions import NotFoundError
from src.shared.schemas import Pagination


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
async def counterparty_id(session):
    counterparty = CounterpartyOrm(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name=f"Test Counterparty {uuid4()}",
        legal_name=f"Test Legal {uuid4()}",
        inn=f"{uuid4().int % 10**10:010d}",
        kpp=None,
        okpo=None,
        phone="+70000000000",
        email=f"cp-{uuid4()}@example.com",
        address=None,
        avatar_url=None,
        contact_persons=[],
        is_active=True,
        parent_id=None,
    )
    session.add(counterparty)
    await session.commit()
    return counterparty.id


class TestUsersRouter:
    @pytest.mark.asyncio
    async def test_get_me_returns_current_user(self, session, user_repo):
        """
        Проверяем handler /users/me: он нужен, чтобы вернуть данные текущего
        пользователя из реального SQL-репозитория.
        Данные: support-пользователь в БД и CurrentUser с его id.
        """
        user = create_support(
            email=f"me-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            user_role=UserRole.SUPPORT_AGENT,
            username="support_me",
            full_name="Support User",
        )
        await user_repo.create(user)
        await session.commit()
        current_user = CurrentUser(
            user_id=user.id,
            email=user.email,
            role=user.role,
            counterparty_id=user.counterparty_id,
        )

        response = await get_me(current_user=current_user, repository=user_repo)

        assert response.id == user.id
        assert response.email == user.email
        assert response.role == user.role

    @pytest.mark.asyncio
    async def test_get_supports_returns_only_support_team(
            self, session, user_repo, counterparty_id
    ):
        """
        Проверяем handler /users/supports: он нужен, чтобы вернуть страницу
        только пользователей из support-команды.
        Данные: support_agent, support_manager и customer в реальной БД.
        """
        support_agent = create_support(
            email=f"agent-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            user_role=UserRole.SUPPORT_AGENT,
            username="support_agent",
            full_name="Support Agent",
        )
        support_manager = create_support(
            email=f"manager-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            user_role=UserRole.SUPPORT_MANAGER,
            username="support_manager",
            full_name="Support Manager",
        )
        customer = create_customer(
            email=f"customer-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=counterparty_id,
            user_role=UserRole.CUSTOMER,
            username="customer_user",
            full_name="Customer User",
        )
        await user_repo.create(support_agent)
        await user_repo.create(support_manager)
        await user_repo.create(customer)
        await session.commit()

        page = await get_supports(
            pagination=Pagination(page=1, size=100),
            repository=user_repo,
        )

        found_ids = {user.id for user in page.items}
        assert {support_agent.id, support_manager.id}.issubset(found_ids)
        assert customer.id not in found_ids
        assert all(
            user.role in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN}
            for user in page.items
        )

    @pytest.mark.asyncio
    async def test_get_users_filters_by_roles(self, session, user_repo, counterparty_id):
        """
        Проверяем handler /users: он нужен, чтобы вернуть страницу пользователей
        с фильтрацией по переданным ролям.
        Данные: customer и support_agent в реальной БД.
        """
        customer = create_customer(
            email=f"customer-filter-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=counterparty_id,
            user_role=UserRole.CUSTOMER,
            username="customer_filter",
            full_name="Customer Filter",
        )
        support_agent = create_support(
            email=f"support-filter-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            user_role=UserRole.SUPPORT_AGENT,
            username="support_filter",
            full_name="Support Filter",
        )
        await user_repo.create(customer)
        await user_repo.create(support_agent)
        await session.commit()

        page = await get_users(
            params=Pagination(page=1, size=100),
            repository=user_repo,
            include_roles=[UserRole.CUSTOMER],
        )

        found_ids = {user.id for user in page.items}
        assert customer.id in found_ids
        assert support_agent.id not in found_ids
        assert all(user.role == UserRole.CUSTOMER for user in page.items)

    @pytest.mark.asyncio
    async def test_get_user_returns_response(self, session, user_repo):
        """
        Проверяем handler /users/{user_id}: он нужен, чтобы вернуть данные
        конкретного пользователя по id.
        Данные: support-пользователь в реальной БД.
        """
        user = create_support(
            email=f"user-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            user_role=UserRole.SUPPORT_AGENT,
            username="single_user",
            full_name="Single User",
        )
        await user_repo.create(user)
        await session.commit()

        response = await get_user(user_id=user.id, repository=user_repo)

        assert response.id == user.id
        assert response.email == user.email
        assert response.role == user.role

    @pytest.mark.asyncio
    async def test_get_user_raises_not_found(self, user_repo):
        """
        Проверяем handler /users/{user_id}: он должен выбросить NotFoundError,
        если пользователь с переданным id не найден.
        Данные: случайный id, которого нет в реальной БД.
        """
        user_id = uuid4()

        with pytest.raises(NotFoundError, match=f"User with ID {user_id} not found"):
            await get_user(user_id=user_id, repository=user_repo)

    @pytest.mark.asyncio
    async def test_get_me_http_returns_current_user(self, session, user_repo):
        """
        Проверяем API endpoint /users/me: он нужен, чтобы FastAPI route,
        dependency get_current_user и SQL-репозиторий вместе вернули текущего пользователя.
        Данные: support-пользователь в реальной БД и CurrentUser с его id.
        """

        user = create_support(
            email=f"http-me-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            user_role=UserRole.SUPPORT_AGENT,
            username="http_me",
            full_name="HTTP User",
        )

        await user_repo.create(user)
        await session.commit()

        current_user = CurrentUser(
            user_id=user.id,
            email=user.email,
            role=user.role,
            counterparty_id=user.counterparty_id,
        )

        from main import app

        app.dependency_overrides[get_user_repo] = lambda: user_repo
        app.dependency_overrides[get_current_user] = lambda: current_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/users/me")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == user.email
        assert data["role"] == user.role
