from typing import Protocol

from uuid import UUID

from ..iam.domain.constants import SUPPORT_TEAM
from ..iam.domain.repos import UserRepository
from ..shared.domain.events import Event
from ..shared.utils.helpers import iterate_batches
from ..tickets.domain.events import TicketCreated
from ..tickets.domain.repos import ProjectRepository
from ..tickets.domain.vo import ProjectRole


class NotificationPolicy[EventT: Event](Protocol):
    """
    Абстрактная политика уведомлений.
    Определяет, кто должен получить уведомление на конкретное событие
    """

    async def get_targets(self, event: EventT) -> list[UUID]:
        """
        Возвращает ID пользователей, которые должны получить уведомление
        """


class TicketCreatedPolicy:
    def __init__(self, project_repo: ProjectRepository, user_repo: UserRepository) -> None:
        self.project_repo = project_repo
        self.user_repo = user_repo

    async def get_targets(self, event: TicketCreated) -> list[UUID]:
        """
        Определение пользователей, которые должны получить уведомление о создании тикета
        """

        targets: set[UUID] = set()

        # 1. Инициатор всегда получает уведомление
        targets.add(event.reporter_id)

        # 2. Администратор клиента всегда получает уведомления
        if event.counterparty_id is not None:
            customer_admins = await self.user_repo.get_customer_admins(event.counterparty_id)
            targets.update({customer_admin.id for customer_admin in customer_admins})

        # 3. Если есть проект - уведомления для поддержки проекта
        if event.project_id is not None:
            project = await self.project_repo.read(event.project_id)
            if project is not None:
                for membership in project.memberships:
                    if membership.is_active and membership.project_role in {
                        ProjectRole.OWNER, ProjectRole.MANAGER, ProjectRole.MEMBER
                    }:
                        targets.add(membership.user_id)

        # 4. Иначе - уведомляем всех сотрудников поддержки
        else:
            async for supports in iterate_batches(self.user_repo, include_roles=[*SUPPORT_TEAM]):
                targets.update({support.id for support in supports})

        return list(targets)
