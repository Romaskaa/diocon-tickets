from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.dtos import TimeRangeFilters

from .vo import Priority, TicketStatus, TicketType


@dataclass(frozen=True)
class ActorsFilters:
    """
    Фильтры по участникам процесса.
    """

    assignee_id: UUID | None = None
    reporter_id: UUID | None = None
    creator_id: UUID | None = None


@dataclass(frozen=True)
class TicketFilters:
    """
    Все возможные фильтры для тикетов.
    """

    search_query: str | None = None
    tags: list[str] | None = None

    counterparty_id: UUID | None = None
    project_ids: set[UUID] | None = None

    statuses: list[TicketStatus] | None = None
    priorities: Priority | None = None
    type: TicketType | None = None

    actors: ActorsFilters | None = None
    time_range: TimeRangeFilters | None = None
