from uuid import uuid4

import pytest

from src.crm.domain.vo import CounterpartyType
from src.crm.infra.models import CounterpartyOrm
from src.iam.domain.services import (
    create_customer,
    create_support,
    invite_customer,
    invite_support,
)
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlInvitationRepository, SqlUserRepository
from src.shared.schemas import Pagination

EXPECTED_SUPPORT_USERS_COUNT = 2


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
def invitation_repo(session):
    return SqlInvitationRepository(session)


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


async def create_counterparty_id(session):
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


class TestSqlUserRepository:
    @pytest.mark.asyncio
    async def test_get_by_email_returns_user(self, session, user_repo, counterparty_id):
        """
        Проверяем SQL-репозиторий пользователей: он нужен, чтобы находить
        сохранённого пользователя по email через реальную БД.
        Данные: customer-пользователь с реальным counterparty_id.
        """
        user = create_customer(
            email=f"user-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=counterparty_id,
            user_role=UserRole.CUSTOMER,
        )
        await user_repo.create(user)
        await session.commit()

        found_user = await user_repo.get_by_email(user.email)

        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.email == user.email

    @pytest.mark.asyncio
    async def test_get_by_email_returns_none(self, user_repo):
        """
        Проверяем SQL-репозиторий пользователей: он должен возвращать None,
        если пользователя с таким email нет в базе.
        Данные: email, который не сохранялся в тестовой БД.
        """
        found_user = await user_repo.get_by_email("missing-user@example.com")

        assert found_user is None

    @pytest.mark.asyncio
    async def test_get_customer_admins_returns_only_admins_for_counterparty(
            self, session, user_repo, counterparty_id
    ):
        """
        Проверяем SQL-репозиторий пользователей: он нужен, чтобы получить только
        customer_admin пользователей конкретного контрагента.
        Данные: админ нужного контрагента, обычный customer и админ другого контрагента.
        """
        other_counterparty_id = await create_counterparty_id(session)
        expected_admin = create_customer(
            email=f"admin-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=counterparty_id,
            user_role=UserRole.CUSTOMER_ADMIN,
        )
        regular_customer = create_customer(
            email=f"customer-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=counterparty_id,
            user_role=UserRole.CUSTOMER,
        )
        other_admin = create_customer(
            email=f"other-admin-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=other_counterparty_id,
            user_role=UserRole.CUSTOMER_ADMIN,
        )
        await user_repo.create(expected_admin)
        await user_repo.create(regular_customer)
        await user_repo.create(other_admin)
        await session.commit()

        admins = await user_repo.get_customer_admins(counterparty_id)

        assert len(admins) == 1
        assert admins[0].id == expected_admin.id
        assert admins[0].role == UserRole.CUSTOMER_ADMIN
        assert admins[0].counterparty_id == counterparty_id

    @pytest.mark.asyncio
    async def test_paginate_filters_by_roles(self, session, user_repo, counterparty_id):
        """
        Проверяем пагинацию SQL-репозитория пользователей: она нужна, чтобы API
        мог отдавать список пользователей только с выбранными ролями.
        Данные: support_agent, support_manager и customer в реальной БД.
        """
        support_agent = create_support(
            email=f"support-agent-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            user_role=UserRole.SUPPORT_AGENT,
        )
        support_manager = create_support(
            email=f"support-manager-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            user_role=UserRole.SUPPORT_MANAGER,
        )
        customer = create_customer(
            email=f"customer-{uuid4()}@example.com",
            password_hash=f"hashed-password-{uuid4()}",
            counterparty_id=counterparty_id,
            user_role=UserRole.CUSTOMER,
        )
        await user_repo.create(support_agent)
        await user_repo.create(support_manager)
        await user_repo.create(customer)
        await session.commit()

        page = await user_repo.paginate(
            Pagination(page=1, size=100),
            include_roles=[UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER],
        )

        found_ids = {user.id for user in page.items}
        assert page.total_items >= EXPECTED_SUPPORT_USERS_COUNT
        assert {support_agent.id, support_manager.id}.issubset(found_ids)
        assert customer.id not in found_ids
        assert all(
            user.role in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER}
            for user in page.items
        )


class TestSqlInvitationRepository:
    @pytest.mark.asyncio
    async def test_get_by_token_returns_invitation(
            self, session, invitation_repo, counterparty_id
    ):
        """
        Проверяем SQL-репозиторий приглашений: он нужен, чтобы находить
        сохранённое приглашение по token через реальную БД.
        Данные: customer-приглашение с реальным counterparty_id.
        """
        invitation = invite_customer(
            invited_by=uuid4(),
            email=f"invitee-{uuid4()}@example.com",
            counterparty_id=counterparty_id,
            assigned_role=UserRole.CUSTOMER,
        )
        await invitation_repo.create(invitation)
        await session.commit()

        found_invitation = await invitation_repo.get_by_token(invitation.token)

        assert found_invitation is not None
        assert found_invitation.id == invitation.id
        assert found_invitation.token == invitation.token

    @pytest.mark.asyncio
    async def test_get_by_token_returns_none(self, invitation_repo):
        """
        Проверяем SQL-репозиторий приглашений: он должен возвращать None,
        если приглашения с таким token нет в базе.
        Данные: token, который не сохранялся в тестовой БД.
        """
        found_invitation = await invitation_repo.get_by_token("missing-token")

        assert found_invitation is None

    @pytest.mark.asyncio
    async def test_get_active_by_email_and_role_returns_unused_invitation(
            self, session, invitation_repo
    ):
        """
        Проверяем поиск активного приглашения: он нужен, чтобы сервис не создавал
        дубликаты для того же email и роли.
        Данные: неиспользованное support-приглашение в реальной БД.
        """
        invitation = invite_support(
            invited_by=uuid4(),
            email=f"support-invite-{uuid4()}@example.com",
            assigned_role=UserRole.SUPPORT_AGENT,
        )
        await invitation_repo.create(invitation)
        await session.commit()

        found_invitation = await invitation_repo.get_active_by_email_and_role(
            invitation.email,
            invitation.assigned_role,
        )

        assert found_invitation is not None
        assert found_invitation.id == invitation.id
        assert found_invitation.is_used is False

    @pytest.mark.asyncio
    async def test_get_active_by_email_and_role_ignores_used_invitation(
            self, session, invitation_repo
    ):
        """
        Проверяем поиск активного приглашения: использованное приглашение
        не должно считаться активным и возвращаться из репозитория.
        Данные: support-приглашение, помеченное как использованное.
        """
        invitation = invite_support(
            invited_by=uuid4(),
            email=f"used-invite-{uuid4()}@example.com",
            assigned_role=UserRole.SUPPORT_AGENT,
        )
        invitation.mark_as_used()
        await invitation_repo.create(invitation)
        await session.commit()

        found_invitation = await invitation_repo.get_active_by_email_and_role(
            invitation.email,
            invitation.assigned_role,
        )

        assert found_invitation is None
