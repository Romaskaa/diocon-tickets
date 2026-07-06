import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID

from src.crm.domain.entities import Counterparty
from src.iam.domain.entities import User
from src.projects.domain.entities import Project

from .domain.entities import Ticket


@dataclass(frozen=True)
class TicketRelations:
    """
    Маппинги для обогащения списка тикетов дополнительной информацией,
    такой как:
     - ФИО пользователей (инициатор и исполнитель)
     - Наименование контрагента
     - Ключ проекта
    """

    user_map: dict[UUID, str] = field(default_factory=dict)
    counterparty_map: dict[UUID, str] = field(default_factory=dict)
    project_map: dict[UUID, str] = field(default_factory=dict)


class TicketReferenceLoader:
    def __init__(
            self,
            users_fetcher: Callable[[list[UUID]], Awaitable[list[User]]],
            counterparties_fetcher: Callable[[list[UUID]], Awaitable[list[Counterparty]]],
            projects_fetcher: Callable[[list[UUID]], Awaitable[list[Project]]]
    ) -> None:
        self.fetch_users = users_fetcher
        self.fetch_counterparties = counterparties_fetcher
        self.fetch_projects = projects_fetcher

    async def load(self, tickets: list[Ticket]) -> TicketRelations:

        if not tickets:
            return TicketRelations()

        # 1. Агрегация ID ключевых сущностей за один проход списка тикетов
        user_ids: set[UUID] = set()
        counterparty_ids: set[UUID] = set()
        project_ids: set[UUID] = set()

        for ticket in tickets:
            user_ids.add(ticket.reporter_id)

            if ticket.assignee_id is not None:
                user_ids.add(ticket.assignee_id)

            if ticket.counterparty_id is not None:
                counterparty_ids.add(ticket.counterparty_id)

            if ticket.project_id is not None:
                project_ids.add(ticket.project_id)

        # 2. Параллельное извлечение агрегированных данных
        async with asyncio.TaskGroup() as tg:
            users_task = tg.create_task(self.fetch_users(list(user_ids)))
            counterparties_task = tg.create_task(
                self.fetch_counterparties(list(counterparty_ids))
            )
            projects_task = tg.create_task(self.fetch_projects(list(project_ids)))

        # 3. Формирование маппингов
        return TicketRelations(
            user_map={user.id: f"{user.full_name}" for user in users_task.result()},
            counterparty_map={
                counterparty.id: counterparty.name
                for counterparty in counterparties_task.result()
            },
            project_map={project.id: f"{project.key}" for project in projects_task.result()},
        )
