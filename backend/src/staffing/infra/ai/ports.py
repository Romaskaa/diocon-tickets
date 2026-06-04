from typing import Protocol

from ...domain.vo import TicketAssigneeCandidate


class TicketAssigneeMatcher(Protocol):
    """Порт для матчинга сотрудников под тикет"""

    async def generate_candidates(self) -> list[TicketAssigneeCandidate]: ...
