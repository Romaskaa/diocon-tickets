from uuid import uuid4

import pytest

from src.projects.domain.entities import Project, ProjectStage
from src.projects.domain.vo import ProjectKey, ProjectRole, ProjectStageStatus, ProjectStatus
from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError, NotFoundError
from src.shared.utils.time import current_datetime


class TestCreate:
    """Тесты для фабричного метода создания проекта"""

    def test_create_should_succeed_with_valid_data(self):
        created_by = uuid4()
        project = Project.create(
            name="  Test project ",
            key="TEST",
            created_by=created_by,
            description="Some description",
            counterparty_id=uuid4(),
        )
        assert project.id is not None
        assert project.name == "Test project"
        assert project.key == ProjectKey("TEST")
        assert project.status == ProjectStatus.ACTIVE
        assert project.owner_id == created_by

    def test_creation_failed_when_empty_name(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            Project.create(name="   ", key="TEST", created_by=uuid4())

    def test_creation_failed_when_key_invalid(self):

        with pytest.raises(ValueError, match="Invalid project key format"):
            Project.create(name="Test", key="1INVALID", created_by=uuid4())


class TestCreateMembership:

    @pytest.mark.parametrize("project_role", list(ProjectRole))
    def test_create_membership_with_any_role_success(self, project_factory, project_role):
        project = project_factory(status=ProjectStatus.ACTIVE)  # Явно указываем статус
        created_by = uuid4()
        membership = project.create_member(
            user_id=uuid4(), project_role=project_role, created_by=created_by,
        )

        assert membership.project_id == project.id
        assert membership.created_by == created_by

    def test_failed_when_project_is_archived(self, project_factory):
        project = project_factory(status=ProjectStatus.ARCHIVED)

        with pytest.raises(InvalidStateError):
            project.create_member(
                user_id=uuid4(), project_role=ProjectRole.CONTRIBUTOR, created_by=uuid4(),
            )


class TestArchive:

    def test_archive_active_project_success(self, project_factory):
        project = project_factory(status=ProjectStatus.ACTIVE)
        project.archive(archived_by=uuid4())

        assert project.status == ProjectStatus.ARCHIVED
        assert project.is_deleted is True

    def test_archive_already_archived_project_do_nothing(self, project_factory):
        """Повторное архивирование проекта не должно менять состояние"""

        project = project_factory(status=ProjectStatus.ARCHIVED, deleted_at=current_datetime())
        project.archive(archived_by=uuid4())
        old_deleted_at = project.deleted_at

        # Повторный вызов
        project.archive(archived_by=uuid4())

        assert old_deleted_at == project.deleted_at


class TestAddStage:
    """Тесты для добавления этапов в проект"""

    def test_add_first_stage_success(self, project_factory):
        project = project_factory()
        old_updated_at = project.updated_at
        stage_name = "  First stage   "
        project.add_stage(name=stage_name)

        assert len(project.stages) == 1
        assert project.stages[0].name == "First stage"
        assert project.stages[0].execution_order == 1
        assert project.updated_at > old_updated_at

    def test_adding_multiple_stages_must_be_sorted(self, project_factory):
        """Список этапов должен быть отсортирован по порядку"""

        project = project_factory()
        num_stages = 5

        for i in range(num_stages):
            project.add_stage(name=f"Stage {i}")

        assert len(project.stages) == num_stages
        # Проверка порядка
        for order, stage in enumerate(project.stages, start=1):
            assert stage.execution_order == order

    def test_indicate_unoccupied_stage_order_success(self, project_factory):
        """
        Можно указать неиспользуемый этап проекта.
        Например, есть 3 этапа (с порядками 1, 2, 3), можно добавить новый
        с порядковым номером 7 (число 7 взято произвольно из свободных кроме 1, 2, 3).
        """

        project = project_factory()
        num_stages = 3

        for i in range(num_stages):
            project.add_stage(name=f"Stage {i}")

        stage_order = 7
        project.add_stage(name="Final stage", execution_order=7)
        assert len(project.stages) == num_stages + 1
        sorted_stages = sorted(project.stages, key=lambda s: s.execution_order)
        assert project.stages == sorted_stages
        assert project.stages[-1].execution_order == stage_order

    @pytest.mark.parametrize("wrong_order", [0, -1, -10, 0.9])
    def test_failed_when_order_is_less_then_one(self, project_factory, wrong_order):
        project = project_factory()

        with pytest.raises(ValueError, match="Stage execution_order must be >= 1"):
            project.add_stage(name="Wrong stage", execution_order=wrong_order)

    def test_failed_when_order_already_exists(self, project_factory):
        project = project_factory()
        num_stages = 3
        for i in range(num_stages):
            project.add_stage(name=f"Stage {i}")

        with pytest.raises(InvariantViolationError, match="already exists"):
            project.add_stage(name="Exists stage", execution_order=3)


class TestReorderStages:
    """Тесты для изменения порядка проведения этапов проекта"""

    @pytest.fixture
    def project_with_stages_factory(self, project_factory):

        def _make_project_with_stages(num_stages: int):
            project = project_factory()
            for i in range(1, num_stages + 1):
                project.add_stage(name=f"Stage {i}")

            return project

        return _make_project_with_stages

    def test_reorder_stages_success(self, project_with_stages_factory):
        project = project_with_stages_factory(num_stages=3)
        # Новый порядок (2, 3, 1)
        new_order = [project.stages[1].id, project.stages[2].id, project.stages[0].id]
        project.reorder_stages(new_order)

        # Проверка по названию этапа
        assert project.stages[0].name == "Stage 2"
        assert project.stages[1].name == "Stage 3"
        assert project.stages[2].name == "Stage 1"

    def test_failed_when_length_does_not_match(self, project_with_stages_factory):
        project = project_with_stages_factory(num_stages=3)

        with pytest.raises(ValueError, match="must contain all stages"):
            project.reorder_stages([uuid4(), uuid4(), uuid4(), uuid4()])

    def test_failed_when_unknown_ids_in_new_order(self, project_with_stages_factory):
        project = project_with_stages_factory(num_stages=3)

        with pytest.raises(ValueError, match="Invalid stage IDs in new execution_order"):
            project.reorder_stages([uuid4(), uuid4(), uuid4()])


class TestStartStage:
    """Начать этап проекта"""

    def test_start_stage_success(self, project_factory):
        project = project_factory()
        num_stages = 3
        for i in range(1, num_stages + 1):
            project.add_stage(name=f"Stage {i}")

        first_stage = project.stages[0]
        project.start_stage(stage_id=first_stage.id, started_by=uuid4())

        assert project.current_stage_id == first_stage.id
        assert project.stages[0].status == ProjectStageStatus.ACTIVE

    def test_failed_when_stage_already_started(self, project_factory):
        project = project_factory()
        project.add_stage(name="Stage 1")
        stage_id = project.stages[0].id
        project.start_stage(stage_id=stage_id, started_by=uuid4())

        with pytest.raises(InvalidStateError):
            project.start_stage(stage_id=stage_id, started_by=uuid4())

    def test_failed_when_project_completed(self, project_factory):
        project_id = uuid4()
        project = project_factory(
            id=project_id,
            stages=[ProjectStage(
                project_id=project_id,
                name="Stage 1",
                order=1,
                status=ProjectStageStatus.COMPLETED,
            )]
        )
        stage_id = project.stages[0].id

        with pytest.raises(InvalidStateError):
            project.start_stage(stage_id=stage_id, started_by=uuid4())


class TestCompleteStage:

    def test_complete_final_stage_with_project_success(self, project_factory):
        """При завершении последней стадии должен завершаться проект"""

        project = project_factory()
        project.add_stage(name="Stage 1")
        stage_id = project.stages[0].id
        project.start_stage(stage_id=stage_id, started_by=uuid4())
        project.complete_stage(stage_id=stage_id, completed_by=uuid4())

        assert project.stages[0].status == ProjectStageStatus.COMPLETED
        assert project.status == ProjectStatus.COMPLETED
        assert project.current_stage_id is None

    def test_failed_when_stage_is_not_active(self, project_factory):
        project = project_factory()
        project.add_stage(name="Stage 1")
        stage_id = project.stages[0].id

        with pytest.raises(InvalidStateError, match="Only ACTIVE stages can be completed"):
            project.complete_stage(stage_id=stage_id, completed_by=uuid4())

    def test_failed_when_stage_does_not_exists(self, project_factory):
        project = project_factory()

        with pytest.raises(NotFoundError, match="does not exist in project"):
            project.complete_stage(stage_id=uuid4(), completed_by=uuid4())
