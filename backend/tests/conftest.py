from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

import src.crm.infra.models
import src.iam.infra.models
from src.crm.dependencies import get_counterparty_repo, get_counterparty_service
from src.crm.domain.entities import Counterparty
from src.crm.domain.repo import CounterpartyRepository
from src.crm.domain.vo import Inn
from src.crm.services import CounterpartyService
from src.iam.dependencies import get_current_user
from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.shared.infra.repos import InMemoryRepository


def pytest_configure(config):
    config.option.asyncio_mode = "auto"

# ====================== In memory реализация репозитория с контрагентами ======================


class InMemoryCounterpartyRepository(InMemoryRepository[Counterparty]):
    async def get_by_email(self, email: str) -> Counterparty | None:
        for entity in self.data.values():
            if entity.email == email:
                return entity
        return None

    async def get_by_inn(self, inn: Inn) -> Counterparty | None:
        for entity in self.data.values():
            if entity.inn == inn:
                return entity
        return None

    async def get_with_descendants(self, counterparty_id: UUID) -> list[Counterparty]:
        return [entity for entity in self.data.values() if entity.parent_id == counterparty_id]


@pytest.fixture
def mock_counterparty_repo() -> CounterpartyRepository:
    return InMemoryCounterpartyRepository()


@pytest.fixture
def mock_counterparty_service(mock_counterparty_repo) -> CounterpartyService:
    return CounterpartyService(session=AsyncMock(), repository=mock_counterparty_repo)


# ====================== Зависимости для тестирования FastAPI ======================


@pytest.fixture
def current_admin_user() -> CurrentUser:
    return CurrentUser(
        user_id=uuid4(),
        email="admin@admin.com",
        role=UserRole.ADMIN,
    )


@pytest.fixture
async def client(
        mock_counterparty_repo, mock_counterparty_service, current_admin_user
) -> AsyncClient:
    from main import app

    # Переопределение зависимостей
    app.dependency_overrides[get_counterparty_repo] = lambda: mock_counterparty_repo
    app.dependency_overrides[get_counterparty_service] = lambda: mock_counterparty_service

    # Добавление аутентифицированного пользователя
    app.dependency_overrides[get_current_user] = lambda: current_admin_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides = {}
