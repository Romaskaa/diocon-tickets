from uuid import UUID

import pytest

from src.tickets.domain.services import TicketScopeService
from src.tickets.loaders import TicketReferenceLoader

# ============================= Доменные сервисы =============================


@pytest.fixture
def ticket_scope_service(fake_membership_repo):
    return TicketScopeService(project_membership_repo=fake_membership_repo)

# ============================= In memory функции загрузчики =============================


@pytest.fixture
def users_fetcher(fake_user_repo):

    async def fetch_users(user_ids: list[UUID]):
        return await fake_user_repo.get_by_ids(user_ids)

    return fetch_users


@pytest.fixture
def counterparties_fetcher(fake_counterparty_repo):

    async def fetch_counterparties(counterparty_ids: list[UUID]):
        return await fake_counterparty_repo.get_by_ids(counterparty_ids)

    return fetch_counterparties


@pytest.fixture
def projects_fetcher(fake_project_repo):

    async def fetch_projects(project_ids: list[UUID]):
        return await fake_project_repo.get_by_ids(project_ids)

    return fetch_projects

# ============================= Data Loader с in memory реализацией =============================


@pytest.fixture
def ticket_data_loader(users_fetcher, counterparties_fetcher, projects_fetcher):
    return TicketReferenceLoader(
        users_fetcher=users_fetcher,
        counterparties_fetcher=counterparties_fetcher,
        projects_fetcher=projects_fetcher,
    )
