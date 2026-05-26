from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import Project
from src.projects.domain.vo import ProjectRole, ProjectStatus
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.projects.schemas import ProjectCreate
from src.projects.services import ProjectService
from src.shared.infra.events import EventBus


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
def event_publisher():
    return EventBus(max_queue_size=10)


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email="project-service-manager@example.com",
        role=UserRole.SUPPORT_MANAGER,
    )


@pytest.fixture
def project_service(session, project_repo, membership_repo, user_repo, event_publisher):
    return ProjectService(
        session=session,
        project_repo=project_repo,
        membership_repo=membership_repo,
        user_repo=user_repo,
        event_publisher=event_publisher,
    )


def make_project(key: str | None = None, owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name=f"Test Project {uuid4()}",
        key=key or f"PR{uuid4().hex[:6].upper()}",
        description="Test project",
        created_by=user_id,
    )


@pytest.mark.asyncio
async def test_create_project_creates_owner_membership(
    project_service,
    membership_repo,
    current_support_manager,
):
    """
    Проверяем ProjectService.create: при создании проекта сервис должен создать
    не только сам проект, но и membership владельца с ролью OWNER.
    Данные: support-manager пользователь и валидная форма создания проекта.
    """

    data = ProjectCreate(
        name=f"Service Project {uuid4()}",
        key=f"SV{uuid4().hex[:6].upper()}",
        description="Created through ProjectService",
        counterparty_id=None,
    )

    response = await project_service.create(data, current_user=current_support_manager)
    membership = await membership_repo.find(
        project_id=response.id,
        user_id=current_support_manager.user_id,
    )

    assert response.name == data.name
    assert response.key == data.key
    assert response.owner_id == current_support_manager.user_id
    assert membership is not None
    assert membership.project_role == ProjectRole.OWNER
    assert membership.added_by == current_support_manager.user_id


@pytest.mark.asyncio
async def test_archive_project_marks_project_archived(
    session,
    project_service,
    project_repo,
    current_support_manager,
):
    """
    Проверяем ProjectService.archive: сервис должен перевести проект в архив,
    сохранить изменения в PostgreSQL и вернуть обновлённую response-схему.
    Данные: активный проект, где текущий пользователь является владельцем.
    """

    project = make_project(
        key=f"AR{uuid4().hex[:6].upper()}",
        owner_id=current_support_manager.user_id,
    )
    await project_repo.create(project)
    await session.commit()

    response = await project_service.archive(
        project_id=project.id,
        current_user=current_support_manager,
    )
    archived_project = await project_repo.read(project.id)

    assert response.id == project.id
    assert response.status == ProjectStatus.ARCHIVED
    assert archived_project is not None
    assert archived_project.status == ProjectStatus.ARCHIVED
    assert archived_project.deleted_at is not None
