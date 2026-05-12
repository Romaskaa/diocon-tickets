from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...tickets.domain.entities import Ticket
    from ...tickets.domain.vo import TicketStatus

import re
from uuid import UUID

from ...iam.domain.services import PermissionResult
from ...iam.domain.vo import UserRole
from ...shared.utils.text import get_latin_slug
from .entities import Project
from .repos import MembershipRepository
from .vo import ProjectRole

WORDS_COUNT = 2
MIN_KEY_LENGTH = 2
MAX_KEY_LENGTH = 10


def generate_project_key(name: str, default: str = "PRJ") -> str:
    """
    Генерирует предложение ключа проекта на основе его имени.

    Алгоритм:
     1. Оставляем только буквы (латиница, кириллица) и пробелы.
     2. Приводим к верхнему регистру.
     3. Берём первые буквы от первых 1-3 слов, если слов несколько.
     4. Если получилось слишком коротко (<2) – берём первые 2-4 буквы первого слова.
     5. Обрезаем до 10 символов.
     6. Если результат всё ещё пуст – возвращаем default.
    """

    if not name:
        return default

    # 1. Только буквы и пробелы (удаление цифр, знаков, эмодзи)
    cleaned = re.sub(r"[^A-Za-zА-Яа-яЁё\s]", "", name)
    cleaned = cleaned.upper()

    # 2. Разбиение на слова
    words = cleaned.split()
    if not words:
        return default

    # 3. Транслитерация слов
    words = [get_latin_slug(word) for word in words]

    # 4. Генерация ключа
    key = "".join(word[0] for word in words[:3]) if len(words) > WORDS_COUNT else words[0][:4]

    # 5. Обеспечение минимальной длины (2 символа)
    if len(key) < MIN_KEY_LENGTH:
        key = (key + key).ljust(2, "X")[:2]  # "А" -> "АА" или "АX"

    # 6. Обрезание до максимальной длины (10 символов)
    key = key[:10]

    # 7. Дополнительная проверка, что первый символ является буквой
    if not key[0].isalpha():
        key = "P" + key[1:] if len(key) > 1 else "PR"

    return key


class ProjectAccessService:
    """
    Доменный сервис для проверки прав доступа к действиям над проектом
    """

    def __init__(self, membership_repo: MembershipRepository) -> None:
        self.membership_repo = membership_repo

    @staticmethod
    def can_create_project(
            user_role: UserRole, project_counterparty_id: UUID | None = None
    ) -> PermissionResult:
        """Может ли пользователь создавать проект"""

        # 1. Менеджер может создавать любой проект
        if user_role in {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
            return PermissionResult(True)

        # 2. Менеджер по работе с клиентами должен указывать контрагента
        if user_role == UserRole.ACCOUNT_MANAGER:
            if project_counterparty_id is not None:
                return PermissionResult(True)

            return PermissionResult(False, "Account manager must specify a counterparty")

        return PermissionResult(False, "Insufficient permissions to create a project")

    async def can_add_members(
            self, project: Project, target_role: ProjectRole, user_id: UUID, user_role: UserRole
    ) -> PermissionResult:
        """Может ли пользователь добавлять участников в проект"""

        # 1. Нельзя назначить владельца проекта через добавление участника
        if target_role == ProjectRole.OWNER:
            return PermissionResult(
                False, "OWNER role cannot be assigned through membership addition"
            )

        # 2. Фактический создатель/админ может добавлять любого участника с любой ролью
        if user_id in {project.created_by, project.owner_id} or user_role == UserRole.ADMIN:
            return PermissionResult(True)

        # 3. Для остальных проверка на членство в проекте
        membership = await self.membership_repo.find(project.id, user_id)
        if membership is None:
            return PermissionResult(False, "Your are not member of the project")

        # 4. Менеджер проекта может добавлять любых участников
        if membership.project_role == ProjectRole.MANAGER:
            return PermissionResult(True)

        # 4.1 Участник может добавлять только ограниченный набор ролей
        if membership.project_role == ProjectRole.CONTRIBUTOR:
            if target_role not in {
                ProjectRole.VIEWER, ProjectRole.CUSTOMER, ProjectRole.CONTRIBUTOR
            }:
                return PermissionResult(
                    False,
                    "Project contributor can add only members with roles: "
                    "CONTRIBUTOR, VIEWER, CUSTOMER"
                )

            return PermissionResult(True)

        # 4.2 Менеджер со стороны клиента может добавлять только клиентов
        if membership.project_role == ProjectRole.CUSTOMER_MANAGER:
            if target_role not in {ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER}:
                return PermissionResult(
                    False,
                    "Customer manager can add only members with roles: CUSTOMER, CUSTOMER_MANAGER"
                )

            return PermissionResult(True)

        return PermissionResult(False, "You do not have permission to add members")

    @staticmethod
    def can_archive_project(
            project: Project, user_id: UUID, user_role: UserRole
    ) -> PermissionResult:
        """Может ли пользователь архивировать проект"""

        # 1. Системный администратор может архивировать любой проект
        if user_role == UserRole.ADMIN:
            return PermissionResult(True)

        # 2. Владелец проекта и фактический создатель могут архивировать проект
        if user_id in {project.created_by, project.owner_id}:
            return PermissionResult(True)

        return PermissionResult(False, "You do not have permission to archive project")

    async def can_transfer_ownership(
            self,
            project: Project,
            target_user_id: UUID,
            user_id: UUID,
            user_role: UserRole,
    ) -> PermissionResult:
        """Может ли пользователь передать владение проектом"""

        # 1. Нельзя передать права самому себе
        if target_user_id == user_id:
            return PermissionResult(False, "You are already the owner")

        # 2. Получение участника, которому хотим передать владение
        target_membership = await self.membership_repo.find(project.id, target_user_id)
        if target_membership is None:
            return PermissionResult(False, "Target owner dose not exist")

        # 3. Запрет передачи прав клиенту
        if target_membership.project_role in {
            ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER,
        }:
            return PermissionResult(False, "Cannot transfer ownership to a customer")

        # 4. Системный администратор может передавать владение даже не находясь в проекте
        if user_role == UserRole.ADMIN:
            return PermissionResult(True)

        # 5. Текущий пользователь должен быть участником проекта
        membership = await self.membership_repo.find(project.id, user_id)
        if membership is None or membership.project_role != ProjectRole.OWNER:
            return PermissionResult(
                False, "Only the project owner or admin can transfer ownership"
            )

        return PermissionResult(True)

    async def can_create_ticket(
            self, project_id: UUID, user_id: UUID, user_role: UserRole
    ) -> PermissionResult:
        """Может ли пользователь создавать тикет внутри проекта"""

        # 1. Администраторы и менеджеры могут создавать тикеты в любом проекте
        if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return PermissionResult(True)

        # 2. Проверка состояние в проекте
        membership = await self.membership_repo.find(project_id, user_id)
        if membership is None or membership.is_deleted:
            return PermissionResult(False, "Your not member of this project")

        # 3. Разрешение на создание тикетов только для следующих ролей внутри проекта
        if membership.project_role in {
            ProjectRole.OWNER,
            ProjectRole.MANAGER,
            ProjectRole.CONTRIBUTOR,
            ProjectRole.CUSTOMER_MANAGER,
            ProjectRole.CUSTOMER,
        }:
            return PermissionResult(True)

        return PermissionResult(False, "You do not have permission to create ticket")

    async def can_view_ticket(
            self, project_id: UUID, user_id: UUID, user_role: UserRole
    ) -> PermissionResult:
        """Может ли пользователь просматривать тикеты внутри проекта"""

        # 1. Администраторы и менеджеры могут просматривать тикеты любого проекта
        if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return PermissionResult(True)

        # 2. Участник должен быть активен
        membership = await self.membership_repo.find(project_id, user_id)
        if membership is None or membership.is_deleted:
            return PermissionResult(False, "Your not member of this project")

        return PermissionResult(True)

    async def can_assign_ticket(
            self, project_id: UUID, assignee_id: UUID, user_id: UUID, user_role: UserRole
    ) -> PermissionResult:
        """Может ли пользователь назначить тикет на себя/другого пользователя"""

        # 1. Администраторы и менеджеры поддержки могут назначать тикеты в любом проекте
        if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return PermissionResult(True)

        # 2. Является ли текущий пользователь участником проекта
        membership = await self.membership_repo.find(project_id, user_id)
        if membership is None or membership.is_deleted:
            return PermissionResult(False, "Your not member of this project")

        # 3. Назначить тикет может только внутренний сотрудник
        if membership.project_role not in {
            ProjectRole.OWNER, ProjectRole.MANAGER, ProjectRole.CONTRIBUTOR
        }:
            return PermissionResult(
                False,
                "Only members with project roles can assign tickets: OWNER, MANAGER, CONTRIBUTOR",
            )

        # 4. Нельзя назначить тикет на несуществующего участника
        target_membership = await self.membership_repo.find(project_id, assignee_id)
        if target_membership is None or target_membership.is_deleted:
            return PermissionResult(False, "Target member dose not exist in this project")

        # 5. Нельзя назначить тикет на клиента/наблюдателя
        if target_membership.project_role in {
            ProjectRole.VIEWER, ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER,
        }:
            return PermissionResult(False, "Cannot assign a ticket to a CLIENT_* or VIEWER")

        return PermissionResult(True)

    async def can_change_ticket_status(  # noqa: C901, PLR0911
            self,
            project_id: UUID,
            ticket: "Ticket",
            new_status: "TicketStatus",
            user_id: UUID,
            user_role: UserRole,
            user_counterparty_id: UUID | None = None,
    ) -> PermissionResult:
        """Может ли пользователь менять статус тикета"""

        from ...tickets.domain.vo import TicketStatus

        # 1. Администраторы и менеджеры поддержки могут менять статус в любом проекте
        if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return PermissionResult(True)

        # 2. Пользователь должен являться участником проекта
        membership = await self.membership_repo.find(project_id, user_id)
        if membership is None or membership.is_deleted:
            return PermissionResult(False, "Your not member of this project")

        # 3. Владелец и менеджер могут менять любые статусы
        if membership.project_role in {ProjectRole.OWNER, ProjectRole.MANAGER}:
            return PermissionResult(True)

        # 4. CONTRIBUTOR не может согласовывать тикеты
        if membership.project_role == ProjectRole.CONTRIBUTOR:
            if ticket.status == TicketStatus.PENDING_APPROVAL:
                return PermissionResult(False, "CONTRIBUTOR cannot approve ticket")

            if new_status in {
                TicketStatus.OPEN,
                TicketStatus.IN_PROGRESS,
                TicketStatus.WAITING,
                TicketStatus.RESOLVED,
                TicketStatus.CLOSED,
            }:
                return PermissionResult(True)

            return PermissionResult(
                False,
                f"Insufficient rights to change to the next status - {new_status}"
            )

        # 5. Менеджер клиента может согласовывать и переоткрывать тикеты своего контрагента
        if membership.project_role in {ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER}:
            if ticket.counterparty_id != user_counterparty_id:
                return PermissionResult(
                    False, "You can only change tickets of your own counterparty"
                )

            # 5.1 Любой клиент может переоткрывать тикет
            if new_status == TicketStatus.REOPENED:
                return PermissionResult(True)

            # 5.2 Только менеджер со стороны клиента может согласовывать тикет
            if (
                    membership.project_role == ProjectRole.CUSTOMER_MANAGER and
                    ticket.status == TicketStatus.PENDING_APPROVAL and
                    new_status in {TicketStatus.OPEN, TicketStatus.REJECTED}
            ):
                return PermissionResult(True)

            return PermissionResult(
                False,
                "Only CUSTOMER_MANAGER can approve tickets in own counterparty"
            )

        return PermissionResult(False)
