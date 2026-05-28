from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.core.database import get_db
from src.iam.dependencies import get_current_user
from src.iam.domain.services import create_support
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import Project
from src.projects.domain.vo import ProjectRole
from src.shared.domain.exceptions import NotFoundError, AlreadyExistsError
from src.iam.domain.exceptions import PermissionDeniedError
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.shared.dependencies import get_event_publisher
from src.shared.infra.events import EventBus


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email="project-manager@example.com",
        role=UserRole.SUPPORT_MANAGER,
    )


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
async def projects_client(session, current_support_manager):
    from main import app

    async def override_get_db():  # noqa: RUF029
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


def make_project(key: str | None = None, owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name=f"Test Project {uuid4()}",
        key=key or f"PR{uuid4().hex[:6].upper()}",
        description="Test project",
        created_by=user_id,
    )


@pytest.mark.asyncio
async def test_get_key_suggestion_returns_generated_key(projects_client):
    """
    Проверяем API предложения ключа проекта: он нужен, чтобы frontend мог
    получить короткий ключ по названию до создания проекта.
    Данные: название проекта, переданное query-параметром name.
    """

    response = await projects_client.get(
        "/api/v1/projects/key-suggestion",
        params={"name": "Customer Portal"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"key": "CUST"}


@pytest.mark.asyncio
async def test_create_project_returns_created_project(projects_client, current_support_manager):
    """
    Проверяем API создания проекта: он должен собрать ProjectService через
    реальные dependencies, сохранить проект в PostgreSQL и вернуть response-схему.
    Данные: support-manager пользователь и валидная форма создания проекта.
    """

    payload = {
        "name": f"Project {uuid4()}",
        "key": f"PR{uuid4().hex[:6].upper()}",
        "description": "Integration project",
        "counterparty_id": None,
    }

    response = await projects_client.post("/api/v1/projects", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["key"] == payload["key"]
    assert data["description"] == payload["description"]
    assert data["owner_id"] == str(current_support_manager.user_id)
    assert data["created_by"] == str(current_support_manager.user_id)


@pytest.mark.asyncio
async def test_check_project_key_returns_unavailable_for_existing_key(session, projects_client, project_repo, current_support_manager):
    """
    Проверяем API проверки ключа проекта: если ключ уже есть в реальной БД,
    endpoint должен вернуть available=False и предложить альтернативы.
    Данные: заранее сохранённый проект с уникальным ключом.
    """

    project_key = f"KEY{uuid4().hex[:5].upper()}"
    project = make_project(key=project_key, owner_id=current_support_manager.user_id)
    await project_repo.create(project)
    await session.commit()

    response = await projects_client.get(f"/api/v1/projects/keys/{project_key}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["available"] is False
    assert data["suggestions"]


@pytest.mark.asyncio
async def test_get_my_projects_returns_current_user_projects(session, projects_client, project_repo, membership_repo, current_support_manager):
    """
    Проверяем API получения моих проектов: он должен вернуть проекты, где текущий
    пользователь является владельцем или участником.
    Данные: один проект во владении пользователя и один проект с его membership.
    """

    other_owner_id = uuid4()
    owned_project = make_project(
        key=f"OWN{uuid4().hex[:6].upper()}",
        owner_id=current_support_manager.user_id,
    )
    member_project = make_project(
        key=f"MEM{uuid4().hex[:6].upper()}",
        owner_id=other_owner_id,
    )
    membership = member_project.create_membership(
        user_id=current_support_manager.user_id,
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=other_owner_id,
    )

    await project_repo.create(owned_project)
    await project_repo.create(member_project)
    await membership_repo.create(membership)
    await session.commit()

    response = await projects_client.get(
        "/api/v1/projects/my",
        params={"page": 1, "size": 10, "owner_only": False},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}
    assert str(owned_project.id) in found_ids
    assert str(member_project.id) in found_ids


@pytest.mark.asyncio
async def test_get_project_returns_project_by_id(session, projects_client, project_repo, current_support_manager):
    """
    Проверяем API получения проекта по id: он должен прочитать проект из
    SQL-репозитория и вернуть публичную response-схему.
    Данные: реальный проект, сохранённый в PostgreSQL.
    """

    project = make_project(
        key=f"GET{uuid4().hex[:6].upper()}",
        owner_id=current_support_manager.user_id,
    )
    await project_repo.create(project)
    await session.commit()

    response = await projects_client.get(f"/api/v1/projects/{project.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(project.id)
    assert data["key"] == str(project.key)
    assert data["name"] == project.name


@pytest.mark.asyncio
async def test_get_projects_returns_paginated_projects(
    session,
    projects_client,
    project_repo,
    current_support_manager,
):
    """
    Проверяем API получения всех проектов: endpoint нужен для админского списка
    проектов и должен вернуть page response из реального SQL-репозитория.
    Данные: два проекта в реальной БД.
    """

    first_project = make_project(
        key=f"LST{uuid4().hex[:6].upper()}",
        owner_id=current_support_manager.user_id,
    )
    second_project = make_project(
        key=f"LST{uuid4().hex[:6].upper()}",
        owner_id=current_support_manager.user_id,
    )

    await project_repo.create(first_project)
    await project_repo.create(second_project)
    await session.commit()

    response = await projects_client.get(
        "/api/v1/projects",
        params={"page": 1, "size": 10},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}

    assert str(first_project.id) in found_ids
    assert str(second_project.id) in found_ids
    assert data["total_items"] >= 2


@pytest.mark.asyncio
async def test_add_member_returns_created_membership(session, projects_client, project_repo, user_repo, current_support_manager):
    """
    Проверяем API добавления участника проекта: он должен найти проект и
    пользователя в реальной БД, создать membership и вернуть данные участника.
    Данные: проект текущего пользователя и support-пользователь для добавления.
    """

    project = make_project(
        key=f"ADD{uuid4().hex[:6].upper()}",
        owner_id=current_support_manager.user_id,
    )
    target_user = create_support(
        email=f"project-member-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        user_role=UserRole.SUPPORT_AGENT,
    )

    await project_repo.create(project)
    await user_repo.create(target_user)
    await session.commit()

    response = await projects_client.post(
        f"/api/v1/projects/{project.id}/memberships",
        json={
            "user_id": str(target_user.id),
            "project_role": ProjectRole.CONTRIBUTOR,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["user_id"] == str(target_user.id)
    assert data["project_role"] == ProjectRole.CONTRIBUTOR
    assert data["added_by"] == str(current_support_manager.user_id)
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_project_not_found_returns_404(projects_client):
    """
    Проверяем API получения проекта по id: если проекта нет в БД,
    endpoint должен вернуть 404.
    Данные: случайный UUID, которого нет в таблице projects.
    """

    project_id = uuid4()

    response = await projects_client.get(f"/api/v1/projects/{project_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(project_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_add_member_project_not_found_returns_404(projects_client):
    """
    Проверяем API добавления участника: если проекта нет,
    endpoint должен вернуть 404.
    Данные: случайный project_id и случайный user_id
    """

    project_id = uuid4()

    response = await projects_client.post(
        f"/api/v1/projects/{project_id}/memberships",
        json = {
            "user_id": str(uuid4()),
            "project_role": ProjectRole.CONTRIBUTOR,
        },
    )

    assert response.status_code == NotFoundError.status_code
    data = response.json()
    assert data["error"]["code"] == NotFoundError.error_code
    assert str(project_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_add_member_user_not_found_returns_404(session, projects_client, project_repo, current_support_manager):
    """
    Проверяем API добавления участника: если пользователь не найден,
    endpoint должен вернуть 404.
    Данные: существует проект и случайный user_id, которого нет в users.
    """

    project = make_project(
        key=f"NF{uuid4().hex[:6].upper()}",
        owner_id=current_support_manager.user_id,
    )

    await project_repo.create(project)
    await session.commit()

    user_id = uuid4()

    response = await projects_client.post(
        f"/api/v1/projects/{project.id}/memberships",
        json = {
            "user_id": str(user_id),
            "project_role": ProjectRole.CONTRIBUTOR,
        }
    )

    assert response.status_code == NotFoundError.status_code
    data = response.json()
    assert data["error"]["code"] == NotFoundError.error_code
    assert str(user_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_add_member_duplicate_returns_409(session, projects_client, project_repo, membership_repo, user_repo, current_support_manager):
    """
    Проверяем API добавления учаcтника: если пользователь уже состоит в проекте,
    endpoint должен вернуть 409.
    Данные: проект, support-пользователь и уже существующий membership.
    """

    project = make_project(
        key=f"DUP{uuid4().hex[:6].upper()}",
        owner_id=current_support_manager.user_id,
    )

    target_user = create_support(
        email=f"duplicate-member-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        user_role=UserRole.SUPPORT_AGENT,
    )

    membership = project.create_membership(
        user_id=target_user.id,
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=current_support_manager.user_id,
    )

    await project_repo.create(project)
    await user_repo.create(target_user)
    await membership_repo.create(membership)
    await session.commit()

    response = await projects_client.post(
        f"/api/v1/projects/{project.id}/memberships",
        json = {
            "user_id": str(target_user.id),
            "project_role": ProjectRole.CONTRIBUTOR,
        }
    )

    assert response.status_code == AlreadyExistsError.status_code
    data = response.json()
    assert data["error"]["code"] == AlreadyExistsError.error_code


@pytest.mark.asyncio
async def test_create_project_forbidden_for_support_agent(session, current_support_manager):
    """
    Проверяем API создания проекта: пользователь без нужной роли
    не должен создавать проект.
    Данные: CurrentUser с ролью SUPPORT_AGENT и валидная форма проекта
    """

    from main import app

    async def override_get_db():  # noqa: RUF029
        yield session

    forbidden_user = CurrentUser(
        user_id=uuid4(),
        email="support-agent@example.com",
        role=UserRole.SUPPORT_AGENT,
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: forbidden_user
    app.dependency_overrides[get_event_publisher] = lambda: EventBus(max_queue_size=10)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/projects",
                json={
                    "name": f"Forbidden Project {uuid4()}",
                    "key": f"FB{uuid4().hex[:6].upper()}",
                    "description": "Should not be created",
                    "counterparty_id": None,
                },
            )
    finally:
        app.dependency_overrides = {}

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["error"]["code"] == "PERMISSION_DENIED"
