from dataclasses import dataclass
from uuid import UUID

from ...iam.domain.vo import UserRole
from ...shared.domain.events import Event
from .vo import CommentType, ReactionType, TicketPriority

# — События для проектов —


@dataclass(frozen=True, kw_only=True)
class ProjectCreated(Event):
    """Проект успешно создан"""

    project_id: UUID
    name: str
    created_by: UUID
    counterparty_id: UUID | None = None

# — События для тикетов –


@dataclass(frozen=True, kw_only=True)
class TicketCreated(Event):
    """Тикет успешно создан"""

    ticket_id: UUID
    title: str
    number: str
    created_by: UUID
    reporter_id: UUID
    priority: TicketPriority
    project_id: UUID | None = None
    counterparty_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class TicketAssigned(Event):
    """Тикет назначен"""

    ticket_id: UUID
    assignee_id: UUID
    assigned_by: UUID
    old_assignee: UUID


@dataclass(frozen=True, kw_only=True)
class TicketStatusChanged(Event):
    """Статус тикета был изменён"""


@dataclass(frozen=True, kw_only=True)
class TicketPriorityChanged(Event):
    """Изменён приоритет тикета"""

    ticket_id: UUID
    number: str
    changed_by: UUID
    old_priority: TicketPriority
    new_priority: TicketPriority


@dataclass(frozen=True, kw_only=True)
class TicketArchived(Event):
    """Тикет архивирован"""

    ticket_id: UUID
    number: str
    reporter_id: UUID
    archived_by: UUID


@dataclass(frozen=True, kw_only=True)
class CommentAdded(Event):
    """Добавлен комментарий"""

    ticket_id: UUID
    comment_id: UUID
    author_id: UUID
    author_role: UserRole
    comment_type: CommentType
    is_public: bool


@dataclass(frozen=True, kw_only=True)
class CommentEdited(Event):
    """Комментарий отредактирован"""

    ticket_id: UUID
    comment_id: UUID
    edited_by: UUID


@dataclass(frozen=True, kw_only=True)
class ReactionAdded(Event):
    """Реакция поставлена"""

    comment_id: UUID
    author_id: UUID
    reaction_type: ReactionType
