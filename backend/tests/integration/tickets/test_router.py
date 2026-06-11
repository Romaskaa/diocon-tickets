from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient, ASGITransport

from src.core.database import get_db
from src.iam.dependencies import get_current_user
from src.iam.domain.services import create_support
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.iam.schemas import CurrentUser
from src.shared.dependencies import get_event_publisher
from src.shared.infra.events import EventBus
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import Priority, Tag, TicketNumber, TicketStatus, TicketType
from src.tickets.infra.repos import SqlTicketRepository


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email=f"ticket-manager-{uuid4()}@example.com",
        role=UserRole.SUPPORT_MANAGER,
        counterparty_id=None,
    )


@pytest.fixture
def ticket_repo(session):
    return SqlTicketRepository(session)


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
async def tickets_client(session, current_support_manager):
    from main import app

    async def override_get_db(): # noqa: RUF029
        yield session


    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_support_manager
    app.dependency_overrides[get_event_publisher] = lambda: EventBus(max_queue_size=10)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides = {}


def make_ticket(*, reporter_id=None, created_by=None, status=TicketStatus.NEW) -> Ticket:
    user_id = created_by or uuid4()

    ticket = Ticket.create(
        ticket_number=TicketNumber(f"INT-26-{uuid4().int % 10**8:08d}"),
        reporter_id=reporter_id or user_id,
        created_by=user_id,
        created_by_role=UserRole.SUPPORT_MANAGER,
        title=f"Router ticket {uuid4()}",
        description="Ticket for router integration test",
        priority=Priority.HIGH,
        tags=[Tag(name="router", color="#3498db")],
    )

    if status != TicketStatus.NEW:
        ticket.change_status(new_status=status, changed_by=user_id)


    return ticket


@pytest.mark.asyncio
async def test_create_ticket_returns_created_ticket(tickets_client, current_support_manager):
    """
    Проверяем API создания тикета: endpoint должен собрать TicketService,
    сохранить тикет в БД и вернуть response-схему.
    Данные: support-manager пользователь и валидная форма создания тикета.
    """

    payload = {
        "reporter_id": str(current_support_manager.user_id),
        "title": f"Created ticket {uuid4()}",
        "description": "Ticket created through router integration test",
        "type": TicketType.INCIDENT,
        "priority": Priority.HIGH,
        "project_id": None,
        "counterparty_id": None,
        "product_id": None,
        "tags": [{"name": "router", "color":"#3498db"}],
    }

    response = await tickets_client.post(
        "/api/v1/tickets",
        json=payload, 
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["reporter_id"] == payload["reporter_id"]
    assert data["created_by"] == str(current_support_manager.user_id)
    assert data["status"] == TicketStatus.NEW
    assert data["priority"] == Priority.HIGH


@pytest.mark.asyncio
async def test_get_ticket_returns_ticket_by_id(session, tickets_client, ticket_repo, current_support_manager,):
    """
    Проверяем API получения тикета по id: endpoint должен прочитать тикет
    из реального SQL-репозитория и вернуть response-схему.
    Данные: зараннее сохранённый тикет в PostgreSQL
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    response = await tickets_client.get(
        f"/api/v1/tickets/{ticket.id}"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(ticket.id)
    assert data["number"] == str(ticket.number)
    assert data["title"] == ticket.title


@pytest.mark.asyncio
async def test_get_ticket_not_found_returns_404(tickets_client):
    """
    Проверяем API получения тикета по id: если тикета нет в БД,
    endpoint должен вернуть 404.
    Данные: случайный UUID, которого нет в таблице tickets.
    """

    ticket_id = uuid4()

    response = await tickets_client.get(
        f"/api/v1/tickets/{ticket_id}"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(ticket_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_get_my_tickets_returns_current_user_reported_tickets(session, tickets_client, ticket_repo, current_support_manager):
    """
    Проверяем API получения моих тикетов: endpoint должен вернуть тольк тикеты,
    где текущий пользователь является reporter_id.
    Данные: один тикет текущего пользователя и один тикет другого reporter.
    """

    my_ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    other_ticket = make_ticket(
        reporter_id=uuid4(),
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(my_ticket)
    await ticket_repo.create(other_ticket)
    await session.commit()

    response = await tickets_client.get(
        "/api/v1/tickets/me",
        params={"page": 1, "size": 10},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    found_ids = {item["id"] for item in data["items"]}

    assert str(my_ticket.id) in found_ids
    assert str(other_ticket.id) not in found_ids
    assert data["total_items"] >= 1


@pytest.mark.asyncio
async def test_update_ticket_returns_updated_ticket(session, tickets_client, ticket_repo, current_support_manager):
    """
    Проверяем API редактирования тикета: endpoint должен найти тикет в БД,
    изменить переданные поля и вернуть обновелённую response-схему.
    Данные: тикет, где текущий пользователь является создателем и reporter.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    payload = {
        "title": "Updated ticket title",
        "description": "Updated ticket description",
        "priority": Priority.CRITICAL,
        "tags": [{"name": "updated", "color": "#ff0000"}],
    }

    response = await tickets_client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json=payload,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["id"] == str(ticket.id)
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["priority"] == payload["priority"]
    assert data["tags"] == payload["tags"] 


@pytest.mark.asyncio
async def test_update_ticket_not_found_returns_404(tickets_client):
    """
    Проверяем API редактирования тикета: если тикета нет в БД,
    endpoint должен вернуть 404.
    Данные: случайный ticket_id.
    """

    ticket_id = uuid4()

    response = await tickets_client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={
            "title": "Missing ticket update",
            "description": "Should not be updated",
            "priority": Priority.HIGH,
            "tags": [],
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(ticket_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_assign_ticket_returns_ticket_with_assignee(session, tickets_client, ticket_repo, user_repo, current_support_manager):
    """
    Проверяем API назначения тикета: endpoint должен найти тикет и пользователя
    в БД, назначить испольнителя и вернуть тикет с assignee_id.
    Данные: существующий тикет и support-agent пользователь.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
        status=TicketStatus.OPEN,
    )

    assignee = create_support(
        email=f"ticket-assignee-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        user_role=UserRole.SUPPORT_AGENT,
    )

    await ticket_repo.create(ticket)
    await user_repo.create(assignee)
    await session.commit()

    response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/assign",
        json={"assignee_id": str(assignee.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(ticket.id)
    assert data["assignee_id"] == str(assignee.id)