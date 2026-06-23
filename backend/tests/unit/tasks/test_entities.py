from decimal import Decimal
from uuid import uuid4

import pytest

from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError
from src.shared.utils.time import current_datetime
from src.tasks.domain.constants import ALLOWED_EDIT_STATUSES
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import StoryPoints, TaskNumber, TaskStatus
from src.tickets.domain.vo import Priority

from .helpers import make_task


@pytest.fixture
def task_number():
    return TaskNumber("TEST-26-00000001-001")


class TestTaskInvariants:
    """
    Тестирование инвариантов задачи
    """

    def test_title_cannot_be_empty(self):
        """
        Заголовок задачи не может быть пустым
        """

        with pytest.raises(ValueError, match="Task title cannot be empty"):
            make_task(title="  ")

    def test_description_cannot_be_empty(self):
        """
        Описание (постановка) задачи не может быть пустым
        """

        with pytest.raises(ValueError, match="Task description cannot be empty"):
            make_task(description="  ")

    def test_cannot_be_in_progress_without_assignee(self, task_number):
        """
        Задача не может быть в работе без назначенного исполнителя
        """

        with pytest.raises(InvariantViolationError, match="without an assignee"):
            Task(
                number=task_number,
                title="Test task",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.MEDIUM,
                assignee_id=None,
                created_by=uuid4(),
            )

    def test_cannot_in_done_status_without_completed_at(self, task_number):
        """
        Задача не может быть выполнена, если не указано время завершения
        """

        with pytest.raises(
                InvariantViolationError, match="Task in 'DONE' status must have completed_at"
        ):
            Task(
                number=task_number,
                title="Test task",
                status=TaskStatus.DONE,
                priority=Priority.MEDIUM,
                completed_at=None,
                created_by=uuid4(),
            )


class TestTaskCreate:

    def test_create_defaults(self, task_number):
        """
        При создании задачи по умолчанию статус - BACKLOG
        """

        task = Task.create(
            number=task_number,
            title="Test task  ",
            description=" Test task description   ",
            created_by=uuid4()
        )

        assert task.number == task_number
        assert task.status == TaskStatus.BACKLOG
        assert task.title == "Test task"
        assert task.description == "Test task description"
        assert task.priority == Priority.MEDIUM

    def test_create_with_all_fields(self, task_number):
        """
        Создание задачи с заполнением всех полей при создании
        """

        ticket_id = uuid4()
        project_id = uuid4()
        due_date = current_datetime().date()

        task = Task.create(
            number=task_number,
            title="Test task",
            created_by=uuid4(),
            description="Test task description",
            priority=Priority.HIGH,
            ticket_id=ticket_id,
            project_id=project_id,
            due_date=due_date,
            estimated_hours=Decimal("3.5"),
        )

        assert task.ticket_id == ticket_id
        assert task.project_id == project_id
        assert task.priority == Priority.HIGH
        assert task.estimated_hours == Decimal("3.5")
        assert task.due_date == due_date


class TestTaskMoveTo:
    @pytest.mark.parametrize(
        ("current_status", "new_status"),
        [
            (TaskStatus.BACKLOG, TaskStatus.TODO),
            (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
            (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED),
            (TaskStatus.IN_PROGRESS, TaskStatus.TO_REVIEW),
            (TaskStatus.TO_REVIEW, TaskStatus.DONE),
            (TaskStatus.TO_REVIEW, TaskStatus.IN_PROGRESS),
        ],
    )
    def test_valid_transition(self, current_status, new_status):
        """
        Успешный перевод задачи к разрешённому статусу
        """

        task = make_task(status=current_status, assignee_id=uuid4())
        task.change_status(new_status, changed_by=uuid4())

        assert task.status == new_status
        assert task.updated_at is not None

    @pytest.mark.parametrize(
        ("current_status", "new_status"),
        [
            (TaskStatus.BACKLOG, TaskStatus.DONE),
            (TaskStatus.DONE, TaskStatus.BACKLOG),
            (TaskStatus.BACKLOG, TaskStatus.BACKLOG),
        ],
    )
    def test_cannot_do_invalid_status_transition(self, current_status, new_status):
        """
        Нельзя перевести задачу в неразрешённый статус
        """

        task = make_task(status=current_status)

        with pytest.raises(InvalidStateError):
            task.change_status(new_status=new_status, changed_by=uuid4())

    def test_sets_started_at_when_moving_to_in_progress(self):
        """
        При переводе в рабочее состояние должно устанавливаться время начала задачи
        """

        task = make_task(status=TaskStatus.TODO, assignee_id=uuid4())
        assert task.started_at is None

        task.change_status(new_status=TaskStatus.IN_PROGRESS, changed_by=uuid4())
        assert task.started_at is not None

    def test_does_not_overwrite_started_at(self):
        """
        Время начала задачи не должно переписываться при переводе в заново рабочий статус
        """

        task = make_task(status=TaskStatus.BLOCKED, assignee_id=uuid4())
        original_start = current_datetime()
        task.started_at = original_start

        task.change_status(TaskStatus.IN_PROGRESS, uuid4())
        assert task.started_at == original_start

    def test_sets_completed_at_when_moving_to_done(self):
        """
        Должно устанавливаться время завершения задачи при переводе в выполнено
        """

        task = make_task(status=TaskStatus.TO_REVIEW)
        assert task.completed_at is None

        task.change_status(new_status=TaskStatus.DONE, changed_by=uuid4())
        assert task.completed_at is not None

    def test_move_to_in_progress_without_assignee_failed(self):
        """
        Нельзя ставить задачу в работе без исполнителя
        """

        task = Task.create(number=TaskNumber("TASK-001"), title="Test task", created_by=uuid4())
        task.change_status(TaskStatus.TODO, changed_by=uuid4())

        with pytest.raises(InvariantViolationError):
            task.change_status(TaskStatus.IN_PROGRESS, changed_by=uuid4())


class TestTaskAssignTo:

    def test_assign_fist_time(self):
        """
        Первичное назначение исполнителя
        """

        task = make_task(status=TaskStatus.TODO)
        assignee_id = uuid4()

        task.assign_to(assignee_id=assignee_id, assigned_by=uuid4())

        assert task.assignee_id == assignee_id

    def test_reassign_same_user_do_nothing(self):
        """
        При переназначении на того же исполнителя не должно меняться состояние объекта
        """

        assignee_id = uuid4()
        task = make_task(status=TaskStatus.TODO, assignee_id=assignee_id)
        original_updated_at = task.updated_at

        task.assign_to(assignee_id=assignee_id, assigned_by=uuid4())

        assert task.updated_at == original_updated_at

    def test_reassign_to_different_user(self):
        """
        Успешное переназначение на другого пользователя
        """

        old_assignee = uuid4()
        new_assignee = uuid4()

        task = make_task(status=TaskStatus.TODO, assignee_id=old_assignee)
        original_updated_at = task.updated_at
        task.assign_to(assignee_id=new_assignee, assigned_by=old_assignee)

        assert task.assignee_id == new_assignee
        assert task.updated_at > original_updated_at

    @pytest.mark.parametrize("status", [TaskStatus.DONE, TaskStatus.CANCELLED])
    def test_cannot_assign_in_not_allowed_status(self, status):
        """
        Нельзя назначить задачу в невалидном статусе
        """

        task = make_task(status=status, assignee_id=uuid4())

        with pytest.raises(InvalidStateError):
            task.assign_to(assignee_id=uuid4(), assigned_by=uuid4())


class TestTaskEdit:

    @pytest.mark.parametrize("status", list(ALLOWED_EDIT_STATUSES))
    def test_edit_success_in_allowed_status(self, status):
        """
        Успешное редактирование тикета в разрешённом статусе
        """

        task = make_task(status=status)
        original_updated_at = task.updated_at

        new_due_date = current_datetime().date()
        task.edit(
            title=" New title ",
            description="New description ",
            priority=Priority.LOW,
            story_points=3,
            estimated_hours=Decimal(8),
            due_date=new_due_date,
        )

        assert task.title == "New title"
        assert task.description == "New description"
        assert task.priority == Priority.LOW
        assert task.story_points == StoryPoints(3)
        assert task.estimated_hours == Decimal(8)
        assert task.due_date == new_due_date
        assert task.updated_at > original_updated_at

    def test_edit_failed_when_empty_title(self):
        """
        Нельзя изменить заголовок на пустой
        """

        task = make_task()

        with pytest.raises(ValueError, match="title cannot be empty"):
            task.edit(title="  ")

    def test_edit_failed_when_negative_estimated_hours(self):
        """
        Нельзя устанавливать отрицательное количество часов
        """

        task = make_task()

        with pytest.raises(ValueError, match="hours cannot be negative"):
            task.edit(estimated_hours=Decimal(-1))

    def test_edit_forbidden_for_deleted_task(self):
        """
        Нельзя редактировать удалённую задачу
        """

        task = make_task(deleted_at=current_datetime())

        with pytest.raises(InvalidStateError, match="Cannot edit deleted task"):
            task.edit(title="New title")

    @pytest.mark.parametrize(
        "status", [status for status in TaskStatus if status not in ALLOWED_EDIT_STATUSES]
    )
    def test_edit_failed_when_not_allowed_status(self, status):
        """
        Нельзя редактировать, когда задача в невалидном статусе
        """

        task = make_task(status=status)

        with pytest.raises(InvalidStateError):
            task.edit(title="New title")


class TestTaskIncrementActualHours:

    def test_add_actual_hours_success(self):
        """
        Успешное добавление факта часов
        """

        task = make_task()
        original_updated_at = task.updated_at
        actual_hours = Decimal("2.5")
        task.add_actual_hours(actual_hours)

        assert task.actual_hours == actual_hours
        assert task.updated_at > original_updated_at

        task.add_actual_hours(Decimal("1.3"))
        assert task.actual_hours == Decimal("3.8")

    def test_add_negative_failed(self):
        """
        Нельзя добавить отрицательное количество часов
        """

        task = make_task()

        with pytest.raises(ValueError, match="Hours must be positive"):
            task.add_actual_hours(Decimal("-1.1"))

    def test_add_to_deleted_task_failed(self):
        """
        Нельзя добавить часы к удалённой задаче
        """

        task = make_task(deleted_at=current_datetime())

        with pytest.raises(InvalidStateError, match="Cannot add hours to archived task"):
            task.add_actual_hours(Decimal("1.1"))


class TestTaskRequestReview:

    def test_request_review_success(self):
        """
        Успешный запрос на ревью задачи
        """

        assignee_id = uuid4()
        reviewer_id = uuid4()
        task = make_task(status=TaskStatus.IN_PROGRESS, assignee_id=assignee_id)

        task.request_review(reviewer_id=reviewer_id, requested_by=uuid4())

        assert task.status == TaskStatus.TO_REVIEW
        assert task.reviewer_id == reviewer_id

    def test_reviewer_cannot_be_assignee(self):
        """
        Нельзя запросить ревью у самого себя
        """

        assignee_id = uuid4()
        task = make_task(status=TaskStatus.IN_PROGRESS, assignee_id=assignee_id)

        with pytest.raises(ValueError, match="Reviewer cannot be the same as assignee"):
            task.request_review(assignee_id, assignee_id)

    def test_review_from_non_in_progress_status_failed(self):
        """
        Запрашивать ревью можно только когда задача в работе
        """

        task = make_task(status=TaskStatus.BACKLOG, assignee_id=uuid4())

        with pytest.raises(InvalidStateError):
            task.request_review(reviewer_id=uuid4(), requested_by=uuid4())


class TestApproveOrRejectReview:

    def test_approve_review_moves_to_done(self):
        """
        Одобренное ревью должно изменить статус задачи на выполненный
        """

        task = make_task(status=TaskStatus.TO_REVIEW, assignee_id=uuid4())
        task.approve_review(approved_by=uuid4())

        assert task.status == TaskStatus.DONE
        assert task.completed_at is not None

    def test_reject_review_moves_back_to_in_progress(self):
        """
        Отклонённое ревью должно возвращать задачу в рабочий статус
        """

        task = make_task(status=TaskStatus.TO_REVIEW, assignee_id=uuid4())
        task.reject_review(rejected_by=uuid4())

        assert task.status == TaskStatus.IN_PROGRESS


class TestTaskArchive:

    def test_archive_success(self):
        """
        Успешное архивирование задачи
        """

        task = make_task()

        assert task.is_deleted is False

        task.archive(archived_by=uuid4())

        assert task.is_deleted is True

    def test_archive_already_archived_do_nothing(self):
        """
        При архивировании уже заархивированной задачи не должно меняться состояние
        """

        task = make_task()
        task.archive(archived_by=uuid4())

        deleted_at = task.deleted_at
        task.archive(archived_by=uuid4())

        assert task.deleted_at == deleted_at
