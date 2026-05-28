import pytest

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from src.shared.schemas import Pagination
from src.shared.utils.time import current_datetime
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import TaskNumber, TaskStatus
from src.tasks.infra.repos import SqlTaskRepository
from src.tickets.domain.vo import Priority


@pytest.fixture
def task_repo(session):
    return SqlTaskRepository(session)


def make_task(
    *,
    number: TaskNumber | None = None,
    status: TaskStatus = TaskStatus.BACKLOG,
    project_id=None,
    ticket_id=None,
    assignee_id=None,
    priority: Priority = Priority.MEDIUM,
    due_date=None,
) -> Task:
    completed_at = current_datetime() if status == TaskStatus.DONE else None

    return Task(
        number=number or TaskNumber(f"TASK-{uuid4().int % 1000:03d}"),
        title=f"Integration task {uuid4()}",
        description="Task for repository integration test",
        status=status,
        priority=priority,
        project_id=project_id,
        ticket_id=ticket_id,
        assignee_id=assignee_id,
        actual_hours=Decimal(0),
        due_date=due_date,
        completed_at=completed_at,
        created_by=uuid4(),
    )


@pytest.mark.asyncio
class TestGetNextSequence:

    async def test_first_call_returns_one(self, task_repo):
        """
        При первом вызове должна возвращаться единица
        """

        sequence = await task_repo.get_next_sequence()
        assert sequence == 1

    async def test_sequential_calls_should_increment_sequence(self, task_repo):
        """
        Последовательные вызовы должны увеличивать последовательность
        """

        first = await task_repo.get_next_sequence()
        assert first == 1

        second = await task_repo.get_next_sequence()
        assert second == 2  # noqa: PLR2004

        third = await task_repo.get_next_sequence()
        assert third == 3  # noqa: PLR2004

    async def test_get_next_sequence_separates_project_sequences(self, task_repo):
        """
        Проверяем последовательность задач по проектам: счётчик должен быть
        отдельным для каждого project_id.
        Данные: два разных project_id в реальной БД.
        """

        first_project_id = uuid4()
        second_project_id = uuid4()

        first_project_sequence = await task_repo.get_next_sequence(
            project_id=first_project_id,
        )
        second_project_sequence = await task_repo.get_next_sequence(
            project_id=second_project_id,
        )
        next_first_project_sequence = await task_repo.get_next_sequence(
            project_id=first_project_id,
        )

        assert first_project_sequence == 1
        assert second_project_sequence == 1
        assert next_first_project_sequence == 2  # noqa: PLR2004

    async def test_get_next_sequence_separates_ticket_sequences(self, task_repo):
        """
        Проверяем последовательность задач по тикетам: счётчик должен быть
        отдельным для каждого ticket_id.
        Данные: два разных ticket_id в реальной БД.
        """

        first_ticket_id = uuid4()
        second_ticket_id = uuid4()

        first_ticket_sequence = await task_repo.get_next_sequence(ticket_id=first_ticket_id)
        second_ticket_sequence = await task_repo.get_next_sequence(ticket_id=second_ticket_id)
        next_first_ticket_sequence = await task_repo.get_next_sequence(
            ticket_id=first_ticket_id,
        )

        assert first_ticket_sequence == 1
        assert second_ticket_sequence == 1
        assert next_first_ticket_sequence == 2  # noqa: PLR2004


@pytest.mark.asyncio
class TestGetByNumber:
    async def test_get_by_number_returns_task(self, session, task_repo):
        """
        Проверяем поиск задачи по номеру: репозиторий должен найти задачу,
        сохранённую в реальную БД.
        Данные: Task с уникальным TaskNumber.
        """

        task_number = TaskNumber(f"TASK-{uuid4().int % 1000:03d}")
        task = make_task(number=task_number)

        await task_repo.create(task)
        await session.commit()

        found = await task_repo.get_by_number(task_number)

        assert found is not None
        assert found.id == task.id
        assert found.number == task_number

    async def test_get_by_number_returns_none(self, task_repo):
        """
        Проверяем поиск задачи по номеру: если номера нет в БД,
        репозиторий должен вернуть None.
        Данные: TaskNumber, которого нет в таблице tasks.
        """

        found = await task_repo.get_by_number(TaskNumber("TASK-999"))

        assert found is None


@pytest.mark.asyncio
class TestGetGroupedByStatus:
    async def test_get_grouped_by_status_returns_tasks_by_status(self, session, task_repo):
        """
        Проверяем основу Kanban-группировки: задачи должны раскладываться
        по колонкам согласно своему статусу.
        Данные: задачи BACKLOG и TODO в реальной БД.
        """

        backlog_task = make_task(number=TaskNumber("TASK-101"), status=TaskStatus.BACKLOG)
        todo_task = make_task(number=TaskNumber("TASK-102"), status=TaskStatus.TODO)

        await task_repo.create(backlog_task)
        await task_repo.create(todo_task)
        await session.commit()

        groups = await task_repo.get_grouped_by_status(Pagination(page=1, size=10))

        backlog_ids = {task.id for task in groups[TaskStatus.BACKLOG].items}
        todo_ids = {task.id for task in groups[TaskStatus.TODO].items}

        assert backlog_task.id in backlog_ids
        assert todo_task.id in todo_ids

    async def test_get_grouped_by_status_filters_by_project_id(self, session, task_repo):
        """
        Проверяем фильтр Kanban-доски по проекту: задачи другого проекта
        не должны попадать в доску текущего проекта.
        Данные: две задачи TODO с разными project_id.
        """

        project_id = uuid4()
        other_project_id = uuid4()
        project_task = make_task(
            number=TaskNumber("TASK-201"),
            status=TaskStatus.TODO,
            project_id=project_id,
        )
        other_project_task = make_task(
            number=TaskNumber("TASK-202"),
            status=TaskStatus.TODO,
            project_id=other_project_id,
        )

        await task_repo.create(project_task)
        await task_repo.create(other_project_task)
        await session.commit()

        groups = await task_repo.get_grouped_by_status(
            Pagination(page=1, size=10),
            project_id=project_id,
        )

        todo_ids = {task.id for task in groups[TaskStatus.TODO].items}

        assert project_task.id in todo_ids
        assert other_project_task.id not in todo_ids

    async def test_get_grouped_by_status_filters_by_assignee_id(self, session, task_repo):
        """
        Проверяем фильтр Kanban-доски по исполнителю: в выборке должны быть
        только задачи нужного assignee_id.
        Данные: две задачи TODO с разными assignee_id.
        """

        assignee_id = uuid4()
        other_assignee_id = uuid4()
        assigned_task = make_task(
            number=TaskNumber("TASK-301"),
            status=TaskStatus.TODO,
            assignee_id=assignee_id,
        )
        other_assigned_task = make_task(
            number=TaskNumber("TASK-302"),
            status=TaskStatus.TODO,
            assignee_id=other_assignee_id,
        )

        await task_repo.create(assigned_task)
        await task_repo.create(other_assigned_task)
        await session.commit()

        groups = await task_repo.get_grouped_by_status(
            Pagination(page=1, size=10),
            assignee_id=assignee_id,
        )

        todo_ids = {task.id for task in groups[TaskStatus.TODO].items}

        assert assigned_task.id in todo_ids
        assert other_assigned_task.id not in todo_ids

    async def test_get_grouped_by_status_filters_overdue_only(self, session, task_repo):
        """
        Проверяем фильтр просроченных задач: overdue_only должен вернуть
        только открытые задачи с due_date в прошлом.
        Данные: просроченная, будущая и завершённая задачи в реальной БД.
        """

        today = current_datetime().date()
        overdue_task = make_task(
            number=TaskNumber("TASK-401"),
            status=TaskStatus.TODO,
            due_date=today - timedelta(days=1),
        )
        future_task = make_task(
            number=TaskNumber("TASK-402"),
            status=TaskStatus.TODO,
            due_date=today + timedelta(days=1),
        )
        done_overdue_task = make_task(
            number=TaskNumber("TASK-403"),
            status=TaskStatus.DONE,
            due_date=today - timedelta(days=1),
        )

        await task_repo.create(overdue_task)
        await task_repo.create(future_task)
        await task_repo.create(done_overdue_task)
        await session.commit()

        groups = await task_repo.get_grouped_by_status(
            Pagination(page=1, size=10),
            overdue_only=True,
        )

        todo_ids = {task.id for task in groups[TaskStatus.TODO].items}
        done_ids = {task.id for task in groups[TaskStatus.DONE].items}

        assert overdue_task.id in todo_ids
        assert future_task.id not in todo_ids
        assert done_overdue_task.id not in done_ids
