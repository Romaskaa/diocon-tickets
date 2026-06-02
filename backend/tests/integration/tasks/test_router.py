from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from main import app
from src.core.database import get_db
from src.iam.dependencies import get_current_user
from src.iam.domain.services import create_support
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import Project
from src.projects.domain.vo import ProjectRole
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.shared.dependencies import get_event_publisher
from src.shared.infra.events import EventBus
from src.shared.utils.time import current_datetime
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import TaskNumber, TaskStatus
from src.tasks.infra.repos import SqlTaskRepository
from src.tickets.domain.vo import Priority


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email=f"manager-{uuid4()}@example.com",
        role=UserRole.SUPPORT_MANAGER,
    )


@pytest.fixture
def task_repo(session):
    return SqlTaskRepository(session)


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
async def tasks_client(session, current_support_manager):

    async def override_get_db():
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


def make_project(owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name=f"Task Project {uuid4()}",
        key=f"TP{uuid4().hex[:6].upper()}",
        description="Project for task router test",
        created_by=user_id,
    )


def make_task(
    *,
    number: TaskNumber | None = None,
    status: TaskStatus = TaskStatus.BACKLOG,
    project_id=None,
    assignee_id=None,
    created_by=None,
) -> Task:
    user_id = created_by or uuid4()

    task = Task.create(
        number=number or TaskNumber(f"TASK-{uuid4().int % 1000:03d}"),
        title=f"Task {uuid4()}",
        description="Task router integration test",
        priority=Priority.MEDIUM,
        project_id=project_id,
        created_by=user_id,
    )

    if assignee_id is not None:
        task.assign_to(assignee_id=assignee_id, assigned_by=user_id)

    if status != TaskStatus.BACKLOG:
        task.move_to(new_status=status, moved_by=user_id)

    return task


@pytest.mark.asyncio
async def test_create_task_returns_created_task(tasks_client, current_support_manager):
    """
    Проверяем API создания задачи: endpoint должен принять данные задачи,
    создать её через реальные зависимости и вернуть response-схему.
    Данные: задача без проекта и тикета, созданная support-manager пользователем.
    """

    response = await tasks_client.post(
        "/api/v1/tasks",
        json={
            "ticket_id": None,
            "project_id": None,
            "title": "Prepare task router tests",
            "description": "Integration test task",
            "priority": Priority.MEDIUM,
            "story_points": 3,
            "assignee_id": None,
            "reviewer_id": None,
            "estimated_hours": 2,
            "due_date": None,
            "tags": [],
            "mark_as_todo": True,
        }
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Prepare task router tests"
    assert data["description"] == "Integration test task"
    assert data["priority"] == Priority.MEDIUM
    assert data["status"] == TaskStatus.TODO
    assert data["created_by"] == str(current_support_manager.user_id)


@pytest.mark.asyncio
async def test_edit_task_updated_task(session, tasks_client, task_repo, current_support_manager):
    """
    Проверяем API редактирования задачи: endpoint должен найти задачу в БД,
    изменить переданные поля и вернуть обновлённую response-схему.
    Данные: существующая задача, созданная текущим пользователем.
    """

    task = make_task(created_by=current_support_manager.user_id)

    await task_repo.create(task)
    await session.commit()

    response = await tasks_client.patch(
        f"/api/v1/tasks/{task.id}",
        json={
            "title": "Updated task title",
            "description": "Updated description",
            "priority": Priority.HIGH,
            "story_points": 5,
            "estimated_hours": 4,
            "due_date": None,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(task.id)
    assert data["title"] == "Updated task title"
    assert data["priority"] == Priority.HIGH
    assert data["story_points"] == 5

    updated_task = await task_repo.read(task.id)

    assert updated_task is not None
    assert updated_task.title == "Updated task title"
    assert updated_task.description == "Updated description"
    assert updated_task.priority == Priority.HIGH
    assert updated_task.story_points is not None
    assert updated_task.story_points.value == 5


@pytest.mark.asyncio
async def test_move_task_status_returns_task_with_new_status(session, tasks_client, task_repo, current_support_manager):
    """
    Проверяем API смены статуса задачи: endpoint должен найти задачу в БД,
    изменить её статус и вернуть обновлённую response-схему.
    Данные: BACKLOG-задача, созданная текущим support-manager пользователем.
    """

    task = make_task(
        status=TaskStatus.TODO,
        assignee_id=current_support_manager.user_id,
        created_by=current_support_manager.user_id,
    )

    await task_repo.create(task)
    await session.commit()

    response = await tasks_client.post(
        f"/api/v1/tasks/{task.id}/status",
        json={
            "new_status": TaskStatus.IN_PROGRESS.value,
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(task.id)
    assert data["status"] == TaskStatus.IN_PROGRESS

    updated_task = await task_repo.read(task.id)

    assert updated_task is not None
    assert updated_task.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_assign_task_returns_task_with_assignee(session, tasks_client, task_repo, user_repo, current_support_manager):
    """
    Проверяем API назначения испольнителя задачи: endpoint должен найти задачу,
    найти пользователя в реальной БД, назначить исполнителя и вернуть обновлённую response-схему.
    Данные: BACKLOG-задача текущего support-manager и support-agent исполнитель.
    """

    task = make_task(
        status=TaskStatus.BACKLOG,
        created_by=current_support_manager.user_id,
    )

    assignee = create_support(
        email=f"task-assignee-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        user_role=UserRole.SUPPORT_AGENT,
    )

    await task_repo.create(task)
    await user_repo.create(assignee)
    await session.commit()

    response = await tasks_client.post(
        f"/api/v1/tasks/{task.id}/assign",
        json={
            "assignee_id": str(assignee.id),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["id"] == str(task.id)
    assert data["assignee_id"] == str(assignee.id)

    updated_task = await task_repo.read(task.id)

    assert updated_task is not None
    assert updated_task.assignee_id == assignee.id


@pytest.mark.asyncio
async def test_archive_task_returns_archived_task(
    session,
    tasks_client,
    task_repo,
    current_support_manager,
):
    """
    Проверяем API архивации задачи: endpoint должен найти задачу,
    пометить её архивной и вернуть обновлённую response-схему.
    Данные: существующая BACKLOG-задача, созданная текущим пользователем.
    """

    task = make_task(
        status=TaskStatus.BACKLOG,
        created_by=current_support_manager.user_id,
    )

    await task_repo.create(task)
    await session.commit()

    response = await tasks_client.delete(f"/api/v1/tasks/{task.id}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == str(task.id)
    assert data["is_archived"] is True

    archived_task = await task_repo.read(task.id)

    assert archived_task is not None
    assert archived_task.deleted_at is not None


@pytest.mark.asyncio
async def test_get_internal_kanban_board_returns_tasks_grouped_by_status(
    session,
    tasks_client,
    task_repo,
    current_support_manager,
):
    """
    Проверяем API kanban-доски: endpoint должен вернуть колонки по статусам
    и положить задачи в соответствующие колонки.
    Данные: BACKLOG и TODO задачи без project_id.
    """

    backlog_task = make_task(
        status=TaskStatus.BACKLOG,
        created_by=current_support_manager.user_id,
    )
    todo_task = make_task(
        status=TaskStatus.TODO,
        created_by=current_support_manager.user_id,
    )

    await task_repo.create(backlog_task)
    await task_repo.create(todo_task)
    await session.commit()

    response = await tasks_client.post(
        "/api/v1/tasks/kanban",
        params={"page": 1, "size": 10},
        json={"type": "internal"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["context"]["type"] == "internal"
    assert data["total_tasks"] >= 2

    columns_by_status = {
        column["status"]: column
        for column in data["columns"]
    }

    backlog_ids = {
        item["id"]
        for item in columns_by_status[TaskStatus.BACKLOG]["tasks"]["items"]
    }
    todo_ids = {
        item["id"]
        for item in columns_by_status[TaskStatus.TODO]["tasks"]["items"]
    }

    assert str(backlog_task.id) in backlog_ids
    assert str(todo_task.id) in todo_ids


@pytest.mark.asyncio
async def test_edit_task_not_found_returns_404(tasks_client):
    """
    Проверяем API редактирования задачи: если задачи нет в БД,
    endpoint должен вернуть 404.
    Данные: случайный task_id.
    """

    task_id = uuid4()

    response = await tasks_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Missing task"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(task_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_assign_task_unknown_user_returns_404(
    session,
    tasks_client,
    task_repo,
    current_support_manager,
):
    """
    Проверяем API назначения исполнителя: если пользователя нет в БД,
    endpoint должен вернуть 404.
    Данные: существующая задача и случайный assignee_id.
    """

    task = make_task(
        status=TaskStatus.BACKLOG,
        created_by=current_support_manager.user_id,
    )
    assignee_id = uuid4()

    await task_repo.create(task)
    await session.commit()

    response = await tasks_client.post(
        f"/api/v1/tasks/{task.id}/assign",
        json={"assignee_id": str(assignee_id)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(assignee_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_request_task_review_returns_task_with_reviewer(
    session,
    tasks_client,
    task_repo,
    user_repo,
    current_support_manager,
):
    """
    Проверяем API запроса ревью задачи: endpoint должен назначить reviewer_id
    и перевести задачу в статус REVIEW.
    Данные: IN_PROGRESS-задача с исполнителем и support-manager как reviewer.
    """

    assignee = create_support(
        email=f"task-review-assignee-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        user_role=UserRole.SUPPORT_AGENT,
    )
    reviewer = create_support(
        email=f"task-reviewer-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        user_role=UserRole.SUPPORT_MANAGER,
    )
    task = make_task(
        status=TaskStatus.IN_PROGRESS,
        assignee_id=assignee.id,
        created_by=current_support_manager.user_id,
    )

    await user_repo.create(assignee)
    await user_repo.create(reviewer)
    await task_repo.create(task)
    await session.commit()

    response = await tasks_client.post(
        f"/api/v1/tasks/{task.id}/request-review",
        json={"reviewer_id": str(reviewer.id)},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == str(task.id)
    assert data["reviewer_id"] == str(reviewer.id)
    assert data["status"] == TaskStatus.REVIEW

    updated_task = await task_repo.read(task.id)

    assert updated_task is not None
    assert updated_task.reviewer_id == reviewer.id
    assert updated_task.status == TaskStatus.REVIEW


@pytest.mark.asyncio
async def test_review_task_approve_returns_done_task(
    session,
    tasks_client,
    task_repo,
    current_support_manager,
):
    """
    Проверяем API ревью задачи: approve должен перевести задачу из REVIEW в DONE.
    Данные: задача в статусе REVIEW, где текущий пользователь является reviewer.
    """

    assignee_id = uuid4()
    task = make_task(
        status=TaskStatus.IN_PROGRESS,
        assignee_id=assignee_id,
        created_by=current_support_manager.user_id,
    )
    task.request_review(
        reviewer_id=current_support_manager.user_id,
        requested_by=assignee_id,
    )

    await task_repo.create(task)
    await session.commit()

    response = await tasks_client.post(
        f"/api/v1/tasks/{task.id}/review",
        json={"action": "approve"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == str(task.id)
    assert data["status"] == TaskStatus.DONE

    updated_task = await task_repo.read(task.id)

    assert updated_task is not None
    assert updated_task.status == TaskStatus.DONE
    assert updated_task.completed_at is not None