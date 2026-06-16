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
from src.projects.domain.entities import Project
from src.projects.domain.vo import ProjectRole
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.tickets.dependencies import get_ticket_data_loader
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import (
    CommentType,
    Priority,
    ReactionType,
    Tag,
    TicketNumber,
    TicketStatus,
    TicketType,
)
from src.tickets.infra.repos import SqlTicketRepository
from src.tickets.loaders import TicketDataLoader


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
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)


@pytest.fixture
async def tickets_client(session, current_support_manager):
    from main import app

    async def override_get_db(): # noqa: RUF029
        yield session

    async def fetch_empty_relations(_ids):
        return []

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_support_manager
    app.dependency_overrides[get_event_publisher] = lambda: EventBus(max_queue_size=10)
    app.dependency_overrides[get_ticket_data_loader] = lambda: TicketDataLoader(
        users_fetcher=fetch_empty_relations,
        counterparties_fetcher=fetch_empty_relations,
        projects_fetcher=fetch_empty_relations,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides = {}


def make_ticket(
    *,
    reporter_id=None,
    created_by=None,
    status=TicketStatus.NEW,
    project_id=None,
    counterparty_id=None,
) -> Ticket:
    user_id = created_by or uuid4()

    ticket = Ticket.create(
        ticket_number=TicketNumber(f"INT-26-{uuid4().int % 10**8:08d}"),
        reporter_id=reporter_id or user_id,
        created_by=user_id,
        created_by_role=UserRole.SUPPORT_MANAGER,
        title=f"Router ticket {uuid4()}",
        description="Ticket for router integration test",
        priority=Priority.HIGH,
        project_id=project_id,
        counterparty_id=counterparty_id,
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


@pytest.mark.asyncio
async def test_change_ticket_status_returns_ticket_with_new_status(session, tickets_client, ticket_repo, current_support_manager):
    """
    Проверяем API смены статуса тикета: endpoint должен найти тикет в БД,
    изменить статус и вернуть обновлённую response-схему.
    Данные: NEW-тикета, созданный текущим support-manager пользователем.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    response = await tickets_client.patch(
        f"/api/v1/tickets/{ticket.id}/status",
        json={
            "status": TicketStatus.OPEN,
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(ticket.id)
    assert data["status"] == TicketStatus.OPEN

    updated_ticket = await ticket_repo.read(ticket.id)
    assert updated_ticket is not None
    assert updated_ticket.status == TicketStatus.OPEN


@pytest.mark.asyncio
async def test_change_ticket_status_not_found_returns_404(tickets_client):
    """
    Проверяем API смены статуса тикета: если тикета нет в БД,
    enpoint должен вернуть 404.
    Данные: случайный ticket_id.
    """

    ticket_id = uuid4()

    response = await tickets_client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={
            "status": TicketStatus.OPEN,
        }
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(ticket_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_delete_ticket_archives_ticket(session, tickets_client, ticket_repo, current_support_manager):
    """
    Проверяем API архивации тикета: endpoint должен выполнить soft-delete
    и вернуть тикет с признаком архивации.
    Данные: существующий тикет текущего support-manager пользователя.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    response = await tickets_client.delete(f"/api/v1/tickets/{ticket.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(ticket.id)
    assert data["is_archived"] is True


@pytest.mark.asyncio
async def test_delete_ticket_not_found_returns_404(tickets_client):
    """
    Проверяем API архивации тикета: если тикета нет в БД,
    endpoint должен вернуть 404.
    Данные: случайеый ticket_id.
    """

    ticket_id = uuid4()

    response = await tickets_client.delete(f"/api/v1/tickets/{ticket_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(ticket_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_add_comment_returns_created_comment(session, tickets_client, ticket_repo, current_support_manager):
    """
    Проверяем API добавления комментария к тикету: endpoint должен найти тикет,
    создать комментарии и вернуть response-схему комментария.
    Данные: существует тикет и public-комментарий текущего пользователя.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={
            "text": "Router integration comment",
            "type": CommentType.PUBLIC,
        }
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["ticket_id"] == str(ticket.id)
    assert data["author_id"] == str(current_support_manager.user_id)
    assert data["author_role"] == current_support_manager.role
    assert data["text"] == "Router integration comment"
    assert data["type"] == CommentType.PUBLIC
    assert data["parent_comment_id"] is None


@pytest.mark.asyncio
async def test_get_ticket_comments_returns_comments_page(session, tickets_client, ticket_repo, current_support_manager):
    """
    Проверяем API получения комментариев тикета: endpoint должен вернуть страницу 
    комментариев с реакциями.
    Данные: существующий тикет и комментарий, созданный через API.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    created_response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={
            "text": "Comment visible in comments page",
            "type": CommentType.PUBLIC,
        }
    )

    assert created_response.status_code == status.HTTP_201_CREATED
    comment_id = created_response.json()["id"]

    response = await tickets_client.get(
        f"/api/v1/tickets/{ticket.id}/comments",
        params={"page": 1, "size": 10}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}

    assert comment_id in found_ids
    assert data["total_items"] >= 1


@pytest.mark.asyncio
async def test_add_comment_reply_returns_created_reply(
    session,
    tickets_client,
    ticket_repo,
    current_support_manager,
):
    """
    Проверяем API ответа на комментарий: endpoint должен найти тикет и
    родительский комментарий, создать reply и вернуть response-схему.
    Данные: существующий тикет и public-комментарий, созданный через API.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    parent_response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={
            "text": "Parent router comment",
            "type": CommentType.PUBLIC,
        },
    )
    assert parent_response.status_code == status.HTTP_201_CREATED
    parent_comment_id = parent_response.json()["id"]

    response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments/{parent_comment_id}/replies",
        json={
            "text": "Router reply comment",
            "type": CommentType.PUBLIC,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["ticket_id"] == str(ticket.id)
    assert data["author_id"] == str(current_support_manager.user_id)
    assert data["text"] == "Router reply comment"
    assert data["type"] == CommentType.PUBLIC
    assert data["parent_comment_id"] == parent_comment_id


@pytest.mark.asyncio
async def test_get_comment_replies_returns_replies_page(
    session,
    tickets_client,
    ticket_repo,
    current_support_manager,
):
    """
    Проверяем API получения ответов на комментарий: endpoint должен вернуть
    страницу replies для родительского комментария.
    Данные: тикет, parent-комментарий и reply, созданные через API.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    parent_response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={
            "text": "Parent comment for replies page",
            "type": CommentType.PUBLIC,
        },
    )
    assert parent_response.status_code == status.HTTP_201_CREATED
    parent_comment_id = parent_response.json()["id"]

    reply_response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments/{parent_comment_id}/replies",
        json={
            "text": "Reply visible in replies page",
            "type": CommentType.PUBLIC,
        },
    )
    assert reply_response.status_code == status.HTTP_201_CREATED
    reply_id = reply_response.json()["id"]

    response = await tickets_client.get(
        f"/api/v1/tickets/comments/{parent_comment_id}/replies",
        params={"page": 1, "size": 10},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}

    assert reply_id in found_ids
    assert data["total_items"] >= 1


@pytest.mark.asyncio
async def test_edit_comment_returns_updated_comment(
    session,
    tickets_client,
    ticket_repo,
    current_support_manager,
):
    """
    Проверяем API редактирования комментария: endpoint должен найти тикет и
    комментарий, обновить текст и вернуть response-схему.
    Данные: тикет и комментарий текущего пользователя.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    created_response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={
            "text": "Comment before edit",
            "type": CommentType.PUBLIC,
        },
    )
    assert created_response.status_code == status.HTTP_201_CREATED
    comment_id = created_response.json()["id"]

    response = await tickets_client.patch(
        f"/api/v1/tickets/{ticket.id}/comments/{comment_id}",
        json={"text": "Comment after edit"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == comment_id
    assert data["ticket_id"] == str(ticket.id)
    assert data["text"] == "Comment after edit"


@pytest.mark.asyncio
async def test_delete_comment_returns_204(
    session,
    tickets_client,
    ticket_repo,
    current_support_manager,
):
    """
    Проверяем API удаления комментария: endpoint должен выполнить soft-delete
    и вернуть 204 No Content.
    Данные: тикет и комментарий текущего пользователя.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    created_response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={
            "text": "Comment to delete",
            "type": CommentType.PUBLIC,
        },
    )
    assert created_response.status_code == status.HTTP_201_CREATED
    comment_id = created_response.json()["id"]

    response = await tickets_client.delete(
        f"/api/v1/tickets/{ticket.id}/comments/{comment_id}",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""

    comments_response = await tickets_client.get(
        f"/api/v1/tickets/{ticket.id}/comments",
        params={"page": 1, "size": 10},
    )
    assert comments_response.status_code == status.HTTP_200_OK
    found_ids = {item["id"] for item in comments_response.json()["items"]}
    assert comment_id not in found_ids


@pytest.mark.asyncio
async def test_toggle_reaction_returns_204(
    session,
    tickets_client,
    ticket_repo,
    current_support_manager,
):
    """
    Проверяем API переключения реакции: endpoint должен создать реакцию
    текущего пользователя и вернуть 204 No Content.
    Данные: тикет и комментарий, созданные через API.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    comment_response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={
            "text": "Comment for reaction",
            "type": CommentType.PUBLIC,
        },
    )
    assert comment_response.status_code == status.HTTP_201_CREATED
    comment_id = comment_response.json()["id"]

    response = await tickets_client.post(
        f"/api/v1/tickets/comments/{comment_id}/reactions",
        json={"reaction_type": ReactionType.LIKE},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


@pytest.mark.asyncio
async def test_get_comment_reactions_returns_reaction_summary(
    session,
    tickets_client,
    ticket_repo,
    current_support_manager,
):
    """
    Проверяем API получения реакций комментария: после toggle endpoint должен
    вернуть счётчик реакции и реакцию текущего пользователя.
    Данные: тикет, комментарий и like-реакция текущего пользователя.
    """

    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await ticket_repo.create(ticket)
    await session.commit()

    comment_response = await tickets_client.post(
        f"/api/v1/tickets/{ticket.id}/comments",
        json={
            "text": "Comment with reaction summary",
            "type": CommentType.PUBLIC,
        },
    )
    assert comment_response.status_code == status.HTTP_201_CREATED
    comment_id = comment_response.json()["id"]

    toggle_response = await tickets_client.post(
        f"/api/v1/tickets/comments/{comment_id}/reactions",
        json={"reaction_type": ReactionType.LIKE},
    )
    assert toggle_response.status_code == status.HTTP_204_NO_CONTENT

    response = await tickets_client.get(f"/api/v1/tickets/comments/{comment_id}/reactions")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["reaction_counts"][ReactionType.LIKE] == 1
    assert ReactionType.LIKE in data["user_reactions"]


@pytest.mark.asyncio
async def test_get_tickets_returns_paginated_ticket_views(
    session,
    tickets_client,
    ticket_repo,
    project_repo,
    membership_repo,
    current_support_manager,
):
    """
    Проверяем API общего списка тикетов: endpoint должен учитывать scope
    текущего support-manager и вернуть страницу TicketViewResponse.
    Данные: проект, membership текущего пользователя и тикет внутри проекта.
    """

    project = Project.create(
        name=f"Ticket Router Project {uuid4()}",
        key=f"TR{uuid4().hex[:6].upper()}",
        created_by=current_support_manager.user_id,
    )
    membership = project.create_membership(
        user_id=current_support_manager.user_id,
        project_role=ProjectRole.MANAGER,
        created_by=current_support_manager.user_id,
    )
    ticket = make_ticket(
        reporter_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
        project_id=project.id,
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await ticket_repo.create(ticket)
    await session.commit()

    response = await tickets_client.get(
        "/api/v1/tickets",
        params={"page": 1, "size": 10},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}

    assert str(ticket.id) in found_ids
    assert data["total_items"] >= 1


@pytest.mark.asyncio
async def test_predict_ticket_fields_returns_prediction(tickets_client, monkeypatch):
    """
    Проверяем API предсказания полей тикета: router должен принять payload,
    вызвать suggest_ticket_fields и вернуть PredictionResponse.
    Данные: функция AI-предсказания заменена стабом, чтобы тест не зависел от внешнего LLM.
    """

    async def fake_suggest_ticket_fields(data):
        return {
            "suggested_priority": Priority.HIGH,
            "suggested_tags": [{"name": "incident", "color": "#ff0000"}],
            "confidence": {"priority": 0.9, "tags": 0.8},
        }

    monkeypatch.setattr(
        "src.tickets.router.suggest_ticket_fields",
        fake_suggest_ticket_fields,
    )

    response = await tickets_client.post(
        "/api/v1/tickets/predict",
        json={
            "title": "Critical production incident",
            "description": "Users cannot log in to the system",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["suggested_priority"] == Priority.HIGH
    assert data["suggested_tags"] == [{"name": "incident", "color": "#ff0000"}]
    assert data["confidence"] == {"priority": 0.9, "tags": 0.8}
