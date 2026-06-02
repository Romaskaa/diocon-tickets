from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.projects.domain.vo import ProjectRole
from src.tickets.domain.services import TicketScopes


@pytest.mark.asyncio
class TestTicketScopeService:

    async def test_admin_has_unrestricted_access(self, ticket_scope_service):
        """Системный администратор имеет неограниченный доступ"""

        scopes = await ticket_scope_service.get_scopes(user_id=uuid4(), user_role=UserRole.ADMIN)
        assert scopes.is_unrestricted()

    @pytest.mark.parametrize(
        "user_role", [
            UserRole.CUSTOMER,
            UserRole.DEVELOPER,
            UserRole.FINANCE,
            UserRole.ACCOUNT_MANAGER,
        ]
    )
    async def test_user_scope_restricts_to_self(self, ticket_scope_service, user_role):
        """Клиент может видеть только свои тикеты (в которых он инициатор)"""

        user_id = uuid4()
        scopes = await ticket_scope_service.get_scopes(user_id=user_id, user_role=user_role)
        assert scopes == TicketScopes(reporter_id=user_id)

    async def test_customer_admin_scope_include_projects(
            self, ticket_scope_service, membership_factory
    ):
        """
        В область видимости администратора контрагента должны входить проекты
        """

        user_id = uuid4()
        user_counterparty_id = uuid4()
        project_ids = [uuid4(), uuid4()]

        await membership_factory(
            user_id=user_id,
            project_id=project_ids[0],
            project_role=ProjectRole.CUSTOMER_MANAGER,
        )
        await membership_factory(
            user_id=user_id,
            project_id=project_ids[1],
            project_role=ProjectRole.CUSTOMER,
        )

        scopes = await ticket_scope_service.get_scopes(
            user_id=user_id,
            user_role=UserRole.CUSTOMER_ADMIN,
            user_counterparty_id=user_counterparty_id,
        )

        assert scopes == TicketScopes(
            counterparty_id=user_counterparty_id, project_ids=project_ids
        )

    async def test_customer_admin_scope_has_not_projects(self, ticket_scope_service):
        """
        Администратор клиента не может видеть тикеты в проектах,
        в которых он не состоит
        """

        counterparty_id = uuid4()
        scopes = await ticket_scope_service.get_scopes(
            user_id=uuid4(),
            user_role=UserRole.CUSTOMER_ADMIN,
            user_counterparty_id=counterparty_id,
        )
        assert scopes == TicketScopes(counterparty_id=counterparty_id, project_ids=[])

    @pytest.mark.parametrize("user_role", [UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER])
    async def test_supports_scope_limited_only_by_project(
            self, ticket_scope_service, user_role, membership_factory
    ):
        """Область видимости поддержки ограничена только проектом"""

        user_id = uuid4()
        project_ids = [uuid4(), uuid4()]

        await membership_factory(
            user_id=user_id,
            project_id=project_ids[0],
            project_role=ProjectRole.CUSTOMER_MANAGER,
        )
        await membership_factory(
            user_id=user_id,
            project_id=project_ids[1],
            project_role=ProjectRole.CUSTOMER,
        )

        scopes = await ticket_scope_service.get_scopes(user_id=user_id, user_role=user_role)
        assert scopes == TicketScopes(project_ids=project_ids)

    @pytest.mark.parametrize("user_role", [UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER])
    async def test_supports_without_projects(self, ticket_scope_service, user_role):
        """Сотрудники поддержки без проекта не могут просматривать тикеты внутри проекта"""

        scopes = await ticket_scope_service.get_scopes(user_id=uuid4(), user_role=user_role)
        assert scopes == TicketScopes(project_ids=[])
