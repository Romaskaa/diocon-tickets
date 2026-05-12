from uuid import UUID, uuid4

import pytest

from src.projects.domain.entities import Project
from src.projects.domain.vo import ProjectKey, ProjectRole, ProjectStatus


@pytest.fixture
def created_by() -> UUID:
    return uuid4()


@pytest.fixture
def counterparty_id() -> UUID:
    return uuid4()


@pytest.fixture
def project_data(created_by, counterparty_id):
    return {
        "name": "Test Project",
        "key": "TEST",
        "created_by": created_by,
        "description": "Test description",
        "counterparty_id": counterparty_id,
    }


@pytest.fixture
def created_project(project_data) -> Project:
    return Project.create(**project_data)


class TestProjectCreate:

    def test_create_should_succeed_with_valid_data(self, project_data):
        """
        Создание проекта с валидными данными
        """

        project = Project.create(**project_data)

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.key == ProjectKey("TEST")
        assert project.status == ProjectStatus.ACTIVE
        assert project.owner_id == project_data["created_by"]

    def test_create_should_raise_error_when_name_empty(self, created_by):
        """
        Должна выбрасываться ошибка при пустом имени
        """

        with pytest.raises(ValueError, match="Project name cannot be empty"):
            Project.create(
                name="   ",
                key="TEST",
                created_by=created_by,
            )

    def test_create_should_raise_error_when_key_invalid(self, created_by):
        """
        Проект не должен создаваться, если задан невалидный ключ
        """

        with pytest.raises(ValueError, match="Invalid project key format"):
            Project.create(
                name="Test",
                key="1INVALID",
                created_by=created_by,
            )


class TestProjectCreateMembership:

    @pytest.mark.parametrize("project_role", list(ProjectRole))
    def test_create_should_succeed_with_any_role(self, created_project, project_role, created_by):
        """
        Успешное создание участника внутри проекта
        """

        membership = created_project.create_membership(
            user_id=uuid4(), project_role=project_role, created_by=created_by,
        )

        assert membership.project_id == created_project.id
        assert membership.added_by == created_by


class TestProjectArchive:

    def test_archive_active_project_success(self, created_project):
        """
        Активный проект должен успешно архивироваться
        """

        created_project.archive(archived_by=uuid4())

        assert created_project.status == ProjectStatus.ARCHIVED
        assert created_project.deleted_at is not None

    def test_archive_already_archived_project_do_nothing(self, created_project):
        """
        При попытке архивации уже заархивированного проекта не должно обновляться состояние
        """

        created_project.archive(archived_by=uuid4())
        old_deleted_at = created_project.deleted_at

        created_project.archive(archived_by=uuid4())

        assert old_deleted_at == created_project.deleted_at
