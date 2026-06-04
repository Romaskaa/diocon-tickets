from uuid import UUID

from ...shared.domain.repo import Repository
from .entities import Employee


class EmployeeRepository(Repository[Employee]):

    async def search_by_embedding(
            self,
            ticket_embedding: list[float],
            limit: int = 20,
            min_similarity: float = 0.65,
            support_line_id: UUID | None = None,
    ) -> list[Employee]:
        """
        Находит сотрудников-кандидатов по семантическому сходству эмбеддингов тикета.
        Это быстрый первый этап (pre-filter + vector search).
        """
