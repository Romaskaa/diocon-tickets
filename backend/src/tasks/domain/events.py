from dataclasses import dataclass
from uuid import UUID

from ...shared.domain.events import Event
from .vo import TaskStatus


@dataclass(frozen=True, kw_only=True)
class TaskCreated(Event):
    """Задача создана"""

    task_id: UUID
    ticket_id: UUID | None = None
    title: str
    created_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskStatusMoved(Event):
    """Статус задачи изменён"""

    task_id: UUID
    ticket_id: UUID | None = None
    old_status: TaskStatus
    new_status: TaskStatus
    moved_by: UUID
