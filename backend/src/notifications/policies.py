from typing import Protocol

from uuid import UUID

from ..iam.domain.constants import SUPPORT_TEAM
from ..iam.domain.repos import UserRepository
from ..projects.domain.repos import ProjectMemberRepository
from ..projects.domain.vo import ProjectRole
from ..shared.domain.events import Event
from ..shared.utils.helpers import iterate_batches
from ..tickets.domain.events import TicketAssigned, TicketCreated


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
    def __init__(
            self, project_membership_repo: ProjectMemberRepository, user_repo: UserRepository
    ) -> None:
        self.project_membership_repo = project_membership_repo
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
            async for members in iterate_batches(
                    self.project_membership_repo,
                    project_id=event.project_id,
                    include_project_roles=[
                        ProjectRole.OWNER, ProjectRole.MANAGER, ProjectRole.CONTRIBUTOR
                    ]
            ):
                targets.update({member.user_id for member in members})

        # 4. Иначе - уведомляем всех сотрудников поддержки
        else:
            async for supports in iterate_batches(self.user_repo, include_roles=[*SUPPORT_TEAM]):
                targets.update({support.id for support in supports})

        return list(targets)


class TicketAssignedPolicy:
    async def get_targets(self, event: TicketAssigned) -> list[UUID]:
        """
        Определяем получателей уведомления о назначении тикета.
        """

        targets = {
            event.assigned_by,
            event.assignee_id,
        }

        if event.old_assignee is not None:
            targets.add(event.old_assignee)

        return list(targets)
