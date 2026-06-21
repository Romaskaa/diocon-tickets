from datetime import date, timedelta
from uuid import uuid4

import pytest

from src.projects.domain.entities import ProjectStage
from src.projects.domain.vo import ProjectStageStatus
from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError
from src.shared.utils.time import current_datetime


class TestInvariants:
    """Тестирование поведения граничных состояний сущности"""

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            ProjectStage(
                project_id=uuid4(),
                name="   ",
                order=1,
                status=ProjectStageStatus.ACTIVE,
            )

    @pytest.mark.parametrize("wrong_order", [0, 0.1, -1])
    def test_order_cannot_be_less_then_one(self, wrong_order):
        with pytest.raises(ValueError, match="cannot be less then 1"):
            ProjectStage(
                project_id=uuid4(),
                name="Stage test",
                order=wrong_order,
                status=ProjectStageStatus.ACTIVE,
            )

    def test_must_valid_planned_period(self):
        with pytest.raises(
                InvariantViolationError,
                match="planned_start date cannot be greater than planned planned_end date"
        ):
            ProjectStage(
                project_id=uuid4(),
                name="Stage test",
                order=1,
                status=ProjectStageStatus.ACTIVE,
                planned_start=date(2026, 6, 15),
                planned_end=date(2026, 6, 12),
            )

    def test_cannot_be_completed_before_it_starts(self):
        with pytest.raises(InvariantViolationError, match="cannot be completed before it starts"):
            ProjectStage(
                project_id=uuid4(),
                name="Stage test",
                order=1,
                status=ProjectStageStatus.ACTIVE,
                started_at=current_datetime() + timedelta(hours=1),
                completed_at=current_datetime(),
            )


class TestEstablishPlannedSchedule:

    def test_planning_success(self, stage_factory):
        stage = stage_factory()
        old_updated_at = stage.updated_at
        stage.establish_planned_schedule(
            start=date(2026, 6, 12), end=date(2026, 6, 15)
        )
        excepted_planned_duration_days = 4
        assert stage.planned_duration_days == excepted_planned_duration_days
        assert stage.is_overdue is False
        assert stage.updated_at > old_updated_at

    def test_failed_when_invalid_planned_period(self, stage_factory):
        stage = stage_factory()

        with pytest.raises(
                ValueError, match="Start planned date cannot be greater than planned planned_end date"
        ):
            stage.establish_planned_schedule(
                start=date(2026, 6, 15), end=date(2026, 6, 12)
            )

    def test_failed_when_panned_start_before_actual_start(self, stage_factory):
        stage = stage_factory(started_at=current_datetime())

        with pytest.raises(InvariantViolationError, match="planned_start date before actual planned_start date"):
            stage.establish_planned_schedule(
                start=date(2026, 6, 11), end=date(2026, 6, 12)
            )


class TestEdit:

    def test_edit_success(self, stage_factory):
        stage = stage_factory(
            name="First stage",
            description="This is first stage",
            responsible_id=uuid4(),
            completion_criteria=["Completed tasks > 10", "Develop MVP"]
        )
        old_updated_at = stage.updated_at
        new_responsible_id = uuid4()
        stage.edit(
            name=" Second stage   ",
            description="This is second stage  ",
            responsible_id=new_responsible_id,
            completion_criteria=["Completed tasks > 20", "Develop MVP"]
        )
        assert stage.name == "Second stage"
        assert stage.description == "This is second stage"
        assert stage.responsible_id == new_responsible_id
        assert stage.completion_criteria == ["Completed tasks > 20", "Develop MVP"]
        assert stage.updated_at > old_updated_at

    def test_edit_sane_fields_do_nothing(self, stage_factory):
        responsible_id = uuid4()
        stage = stage_factory(
            name="First stage",
            description="This is first stage",
            responsible_id=responsible_id,
            completion_criteria=["Completed tasks > 10", "Develop MVP"],
        )
        old_updated_at = stage.updated_at
        stage.edit(
            name=" First stage ",
            description="  This is first stage",
            responsible_id=responsible_id,
            completion_criteria=["Completed tasks > 10", "Develop MVP"],
        )
        assert stage.name == "First stage"
        assert stage.description == "This is first stage"
        assert stage.updated_at == old_updated_at


class TestStart:

    def test_start_success(self, stage_factory):
        stage = stage_factory(status=ProjectStageStatus.PLANNED)
        old_updated_at = stage.updated_at
        stage.planned_start(started_by=uuid4())

        assert stage.started_at is not None
        assert stage.status == ProjectStageStatus.ACTIVE
        assert stage.updated_at > old_updated_at

    @pytest.mark.parametrize(
        "wrong_status",
        [
            ProjectStageStatus.ACTIVE,
            ProjectStageStatus.COMPLETED,
            ProjectStageStatus.ON_HOLD,
            ProjectStageStatus.SKIPPED,
        ],
    )
    def test_failed_when_not_planned_status(self, stage_factory, wrong_status):
        stage = stage_factory(status=wrong_status)

        with pytest.raises(InvalidStateError, match="Only PLANNED stage can be started"):
            stage.planned_start(started_by=uuid4())


class TestComplete:

    def test_complete_success(self, stage_factory):
        stage = stage_factory(status=ProjectStageStatus.ACTIVE)
        old_updated_at = stage.updated_at
        stage.complete(completed_by=uuid4())

        assert stage.completed_at is not None
        assert stage.status == ProjectStageStatus.COMPLETED
        assert stage.updated_at > old_updated_at

    @pytest.mark.parametrize(
        "wrong_status",
        [
            ProjectStageStatus.PLANNED,
            ProjectStageStatus.COMPLETED,
            ProjectStageStatus.ON_HOLD,
            ProjectStageStatus.SKIPPED
        ]
    )
    def test_failed_when_not_active_status(self, stage_factory, wrong_status):
        stage = stage_factory(status=wrong_status)

        with pytest.raises(InvalidStateError, match="Only ACTIVE stage can be completed"):
            stage.complete(completed_by=uuid4())
