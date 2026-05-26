from uuid import uuid4

import pytest

from src.projects.domain.entities import Project
from src.projects.domain.vo import ProjectKey, ProjectRole
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.shared.schemas import Pagination


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)

def make_project(key: str | None = None, owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name="Test Project {uuid4()}",
        key=key or f"PR{uuid4().hex[:6].upper()}",
        description="Test project",
        created_by=user_id,
    )

@pytest.mark.asyncio
async def test_get_by_key_returns_project(session, project_repo):
    """
    Проверяем SQL-репозитории проектов: он нужен, чтобы сервис мог найти
    проект по уникальному ключу перед созданием или проверкой доступности ключа.
    Данные: реальный Project, сохранённый в PostgreSQL.
    """

    project = make_project(key="TESTKEY")

    await project_repo.create(project)
    await session.commit()

    found = await project_repo.get_by_key(ProjectKey("TESTKEY"))

    assert found is not None
    assert found.id == project.id
    assert found.key == ProjectKey("TESTKEY")


@pytest.mark.asyncio
async def test_get_by_key_returns_none(project_repo):
    """
    Проверяем SQL-репозиторий проектов: если проекта с таким ключом нет, 
    метод должен вернуть None, а не падать с ошибкой.
    Данные: ключ, которого нет в реальной БД.
    """

    found = await project_repo.get_by_key(ProjectKey("UNKNOWN"))

    assert found is None

@pytest.mark.asyncio
async def test_get_existing_keys_returns_only_existing_keys(session, project_repo):
    """
    Проверяем поиск существующих ключей: он нужен для генерации свободных
    вариантов ключа при конфликте уникальности.
    Данные: два проекта в реальной БД и один отсутствующий ключ.
    """

    first_project = make_project(key="EXIST1")
    second_project = make_project(key="EXIST2")

    await project_repo.create(first_project)
    await project_repo.create(second_project)
    await session.commit()

    existing_keys = await project_repo.get_existing_keys(["EXIST1", "EXIST2", "FREEKEY"])

    assert existing_keys == {"EXIST1", "EXIST2"}


@pytest.mark.asyncio
async def test_membership_find_returns_membership(session, project_repo, membership_repo):
    """
    Проверяем SQL-репозиторий участников проекта: он нужен для проверки прав
    пользователя внутри конкретного проекта.
    Данные: проект и учатники проекта с ролью CONTRIBUTOR в реальной БД.
    """

    owner_id = uuid4()
    member_id = uuid4()
    project = make_project(key="MEMBER1", owner_id=owner_id)
    membership = project.create_membership(
        user_id=member_id,
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=owner_id,
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await session.commit()

    found = await membership_repo.find(project.id, member_id)

    assert found is not None
    assert found.id == membership.id
    assert found.project_id == project.id
    assert found.user_id == member_id
    assert found.project_role == ProjectRole.CONTRIBUTOR


@pytest.mark.asyncio
async def test_get_existing_keys_with_empty_list_returns_empty_set(project_repo):
    """
    Проверяем SQL-репозиторий проектов: если список ключей пустой,
    метод должен сразу вернуть пустой set и не делать лишний SQL-запрос.
    Данные: пустой список ключей.
    """

    existing_keys = await project_repo.get_existing_keys([])

    assert existing_keys == set()


@pytest.mark.asyncio
async def test_get_by_user_membership_returns_owned_and_member_projects(session, project_repo, membership_repo):
    """
    Проверяем SQL-репозиторий проектов: он должен вернуть проекты,
    где пользователь является владельцем или участником.
    Данные: один проект пользователя как владельца, один проект как участника
    и один чужой проект.
    """

    user_id = uuid4()
    other_owner_id = uuid4()

    owned_project = make_project(
        key=f"OWN{uuid4().hex[:6].upper()}",
        owner_id=user_id,
    )
    member_project = make_project(
        key=f"MEM{uuid4().hex[:6].upper()}",
        owner_id=other_owner_id,
    )
    unrelated_project = make_project(
        key=f"OUT{uuid4().hex[:6].upper()}",
        owner_id=uuid4(),
    )
    membership = member_project.create_membership(
        user_id=user_id,
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=other_owner_id,
    )

    await project_repo.create(owned_project)
    await project_repo.create(member_project)
    await project_repo.create(unrelated_project)
    await membership_repo.create(membership)
    await session.commit()

    page = await project_repo.get_by_user_membership(
        user_id=user_id,
        pagination=Pagination(page=1, size=10),
        owner_only=False,
    )

    found_ids = {project.id for project in page.items}

    assert page.total_items == 2
    assert owned_project.id in found_ids
    assert member_project.id in found_ids
    assert unrelated_project.id not in found_ids


@pytest.mark.asyncio
async def test_get_by_user_membership_owner_only_returns_only_owned_projects(session, project_repo, membership_repo):
    """
    Проверяем SQL-репозиторий проектов: с owner_only=True должны вернуться
    только проекты, где пользователь является владельцем.
    Данные: один собственный проект и один проект, где пользователь просто участник.
    """

    user_id = uuid4()
    other_owner_id = uuid4()

    owned_project = make_project(
        key=f"OWN{uuid4().hex[:6].upper()}",
        owner_id=user_id,
    )
    member_project = make_project(
        key=f"MEM{uuid4().hex[:6].upper()}",
        owner_id=other_owner_id,
    )
    membership = member_project.create_membership(
        user_id=user_id,
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=other_owner_id,
    )

    await project_repo.create(owned_project)
    await project_repo.create(member_project)
    await membership_repo.create(membership)
    await session.commit()

    page = await project_repo.get_by_user_membership(
        user_id=user_id,
        pagination=Pagination(page=1, size=10),
        owner_only=True,
    )

    found_ids = {project.id for project in page.items}

    assert page.total_items == 1
    assert owned_project.id in found_ids
    assert member_project.id not in found_ids


@pytest.mark.asyncio
async def test_membership_paginate_filters_by_project_id(session, project_repo, membership_repo):
    """
    Проверяем пагинацию участников проекта: она должна возвращать участников
    только конкретного проекта.
    Данные: два проекта и по одному участнику в каждом.
    """

    owner_id = uuid4()

    first_project = make_project(
        key=f"PR{uuid4().hex[:6].upper()}",
        owner_id=owner_id,
    )
    second_project = make_project(
        key=f"PR{uuid4().hex[:6].upper()}",
        owner_id=owner_id,
    )
    first_membership = first_project.create_membership(
        user_id=uuid4(),
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=owner_id,
    )
    second_membership = second_project.create_membership(
        user_id=uuid4(),
        project_role=ProjectRole.VIEWER,
        created_by=owner_id,
    )

    await project_repo.create(first_project)
    await project_repo.create(second_project)
    await membership_repo.create(first_membership)
    await membership_repo.create(second_membership)
    await session.commit()

    page = await membership_repo.paginate(
        Pagination(page=1, size=10),
        project_id=first_project.id,
    )

    assert page.total_items == 1
    assert page.items[0].id == first_membership.id


@pytest.mark.asyncio
async def test_membership_paginate_filters_by_project_roles(session, project_repo, membership_repo):
    """
    Проверяем пагинацию участников проекта: она должна уметь возвращать
    только участников с нужными проектными ролями.
    Данные: один проект с manager и viewer участниками.
    """

    owner_id = uuid4()
    project = make_project(
        key=f"ROLE{uuid4().hex[:6].upper()}",
        owner_id=owner_id,
    )
    manager_membership = project.create_membership(
        user_id=uuid4(),
        project_role=ProjectRole.MANAGER,
        created_by=owner_id,
    )
    viewer_membership = project.create_membership(
        user_id=uuid4(),
        project_role=ProjectRole.VIEWER,
        created_by=owner_id,
    )

    await project_repo.create(project)
    await membership_repo.create(manager_membership)
    await membership_repo.create(viewer_membership)
    await session.commit()

    page = await membership_repo.paginate(
        Pagination(page=1, size=10),
        project_id=project.id,
        include_project_roles=[ProjectRole.MANAGER],
    )

    assert page.total_items == 1
    assert page.items[0].id == manager_membership.id
    assert page.items[0].project_role == ProjectRole.MANAGER