from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import AlreadyExistsError
from src.tickets.domain.entities import Project
from src.tickets.schemas import ProjectCreate
from src.tickets.services import ProjectService


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def project_service(mock_session, mock_project_repo, event_publisher):
    return ProjectService(mock_session, mock_project_repo, event_publisher)


@pytest.fixture
async def sample_project(mock_project_repo):
    project = Project.create(
        name="Test Project",
        key="TEST",
        owner_id=uuid4(),
        created_by=uuid4(),
    )
    await mock_project_repo.create(project)
    return project


class TestCheckKey:
    """
    Тесты для методы проверки ключа
    """

    @pytest.mark.asyncio
    async def test_check_key_available_when_key_not_exists(self, project_service):
        response = await project_service.check_key("NEWKEY")

        assert response.available is True
        assert response.suggestions == []

    @pytest.mark.asyncio
    async def test_check_key_not_available_when_key_exists(self, project_service, sample_project):  # noqa: ARG002
        response = await project_service.check_key("TEST")

        assert response.available is False
        assert len(response.suggestions) > 0
        assert "TEST1" in response.suggestions or "TEST-1" in response.suggestions


class TestGenerateKeySuggestions:
    """
    Тестирование генерации вариантов уникальных ключей проекта
    """

    @pytest.mark.asyncio
    async def test_generate_suggestions_returns_unique_available_keys(
        self, project_service, sample_project  # noqa: ARG002
    ):
        suggestions = await project_service.generate_key_suggestions("TEST", max_attempts=3)

        assert "TEST" not in suggestions
        assert "TEST1" in suggestions
        assert "TEST2" in suggestions

    @pytest.mark.asyncio
    async def test_generate_suggestions_fallback_when_empty_base(self, project_service):
        suggestions = await project_service.generate_key_suggestions("", max_attempts=2)

        assert suggestions[0] == "PROJ1"
        assert suggestions[1] == "PROJ2"

    @pytest.mark.asyncio
    async def test_generate_suggestions_respects_max_attempts(self, project_service):
        suggestions = await project_service.generate_key_suggestions("WEB", max_attempts=2)
        excepted_suggestions_count = 2

        assert len(suggestions) <= excepted_suggestions_count
        assert "WEB1" in suggestions
        assert "WEB2" in suggestions


class TestCreateProject:
    """
    Тестирование для метода создания проекта
    """

    async def test_create_success(self, project_service, mock_session, mock_project_repo):
        data = ProjectCreate(name="New Project", key="NEW", owner_id=uuid4())
        created_by = uuid4()

        response = await project_service.create(data, created_by)

        assert response.key == "NEW"
        assert response.name == "New Project"
        mock_session.commit.assert_awaited_once()

        # Проверка на успешное сохранение
        existing_project = await mock_project_repo.read(response.id)

        assert existing_project is not None
        assert existing_project.key.value == "NEW"

    async def test_create_with_key_conflict_retries_with_suffix(
        self, project_service, mock_session, sample_project  # noqa: ARG002
    ):
        # Создание проекта с занятым ключом
        data = ProjectCreate(name="Another Project", key="TEST", owner_id=uuid4())
        created_by = uuid4()

        # Первый вызов Project.create должен пройти, но при flush возникнет ошибка уникальности
        with patch.object(
            project_service.repository,
            "create",
            side_effect=[
                IntegrityError("duplicate key", None, None),
                None,
            ],
        ):
            response = await project_service.create(data, created_by, max_attempts=3)

        assert response.key == "TEST1"

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    async def test_create_fails_after_max_attempts(
        self, project_service, mock_session, sample_project  # noqa: ARG002
    ):
        data = ProjectCreate(name="Failing Project", key="TEST", owner_id=uuid4())
        created_by = uuid4()

        with patch.object(
            project_service.repository,
            "create",
            side_effect=IntegrityError("duplicate", None, None),
        ):
            with pytest.raises(AlreadyExistsError) as exc:
                await project_service.create(data, created_by, max_attempts=2)

            assert "2 attempts were not enough" in str(exc.value)
            assert exc.value.details["last_suggested_key"] == "TEST2"
