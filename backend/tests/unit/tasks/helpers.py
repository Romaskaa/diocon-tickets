from decimal import Decimal
from uuid import uuid4

from src.shared.utils.time import current_datetime
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import TaskNumber, TaskStatus
from src.tickets.domain.vo import TicketPriority


def make_task(*, status: TaskStatus = TaskStatus.BACKLOG, **overrides) -> Task:
    """Фабрика для создания задач"""

    assignee_id = overrides.pop("assignee_id", None)
    completed_at = overrides.pop("completed_at", None)

    if status == TaskStatus.IN_PROGRESS and assignee_id is None:
        assignee_id = uuid4()
    if status == TaskStatus.DONE and completed_at is None:
        completed_at = current_datetime()

    return Task(
        id=overrides.pop("id", uuid4()),
        number=overrides.pop("number", TaskNumber("TEST-26-00000001-001")),
        title=overrides.pop("title", "Test task"),
        description=overrides.pop("description", None),
        status=status,
        priority=overrides.pop("priority", TicketPriority.MEDIUM),
        assignee_id=assignee_id,
        reviewer_id=overrides.pop("reviewer_id", None),
        estimated_hours=overrides.pop("estimated_hours", None),
        actual_hours=overrides.pop("actual_hours", Decimal(0)),
        due_date=overrides.pop("due_date", None),
        started_at=overrides.pop("started_at", None),
        completed_at=completed_at,
        created_by=overrides.pop("created_by", uuid4()),
        created_at=overrides.pop("created_at", current_datetime()),
        updated_at=overrides.pop("updated_at", current_datetime()),
        deleted_at=overrides.pop("deleted_at", None),
        **overrides,
    )
