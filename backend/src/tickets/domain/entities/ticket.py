from typing import Self

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ....iam.domain.exceptions import PermissionDeniedError
from ....iam.domain.vo import UserRole
from ....media.domain.entities import Attachment
from ....shared.domain.entities import AggregateRoot, Entity
from ....shared.domain.exceptions import InvariantViolationError
from ....shared.utils.time import current_datetime
from ..constants import (
    ALLOWED_ASSIGN_STATUSES,
    ALLOWED_EDIT_STATUSES,
    ALLOWED_TRANSITIONS,
)
from ..events import (
    TicketArchived,
    TicketAssigned,
    TicketCreated,
    TicketPriorityChanged,
)
from ..vo import (
    Tag,
    TicketNumber,
    TicketPriority,
    TicketStatus,
)


@dataclass(kw_only=True)
class TicketHistoryEntry(Entity):
    """
    Запись в истории изменения тикета.
    Всегда заполняется автоматически внутри бизнес-методов.
    """

    ticket_id: UUID
    actor_id: UUID  # Кто совершил действие
    action: str  # 'status_changed', 'assigned', 'comment_added'
    old_value: str | None = None
    new_value: str | None = None
    description: str = field(default="")  # Человеко-читаемое описание


@dataclass(kw_only=True)
class Ticket(AggregateRoot):
    """
    Агрегат Тикет — центральная сущность системы
    """

    project_id: UUID | None = None
    counterparty_id: UUID | None = None
    product_id: UUID | None = None

    # Ключевые поля
    created_by: UUID  # Технический создатель
    created_by_role: UserRole
    reporter_id: UUID  # Инициатор/автор проблемы (тот кто пожаловался)

    number: TicketNumber
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    assigned_to: UUID | None = None
    closed_at: datetime | None = None

    # Дополнительно
    tags: list[Tag] = field(default_factory=list)

    # Внутренние коллекции агрегата
    attachments: list[Attachment] = field(default_factory=list)
    history: list[TicketHistoryEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        # 1. Заголовок не должен быть пустым
        if not self.title.strip():
            raise ValueError("Title cannot be empty")

        # 2. если тикет создан клиентом - контрагент должен быть заполнен
        if self.created_by_role.is_customer() and self.counterparty_id is None:
            raise InvariantViolationError(
                "Customer-created ticket must be linked to a counterparty"
            )

    @classmethod
    def create(
        cls,
        ticket_number: TicketNumber,
        reporter_id: UUID,
        created_by: UUID,
        created_by_role: UserRole,
        title: str,
        description: str | None = None,
        priority: TicketPriority = TicketPriority.MEDIUM,
        project_id: UUID | None = None,
        counterparty_id: UUID | None = None,
        product_id: UUID | None = None,
        tags: list[Tag] | None = None,
    ) -> Self:
        """Создание тикета"""

        # 1. Создание доменной сущности
        ticket_id = uuid4()
        initial_status = (
            TicketStatus.PENDING_APPROVAL if created_by_role.is_customer() else TicketStatus.NEW
        )
        ticket = cls(
            id=ticket_id,
            created_by_role=created_by_role,
            created_by=created_by,
            reporter_id=reporter_id,
            number=ticket_number,
            title=title,
            description=description,
            priority=priority,
            status=initial_status,
            project_id=project_id,
            counterparty_id=counterparty_id,
            product_id=product_id,
            tags=tags if tags is not None else [],
            history=[
                TicketHistoryEntry(
                    ticket_id=ticket_id,
                    actor_id=created_by,
                    action="ticket_created",
                    description=f"Создан новый тикет - {ticket_number}",
                )
            ],
        )

        # 2. Регистрация доменного события
        ticket.register_event(
            TicketCreated(
                ticket_id=ticket_id,
                title=title,
                number=f"{ticket_number}",
                created_by=created_by,
                reporter_id=reporter_id,
                priority=priority,
                counterparty_id=counterparty_id,
            )
        )

        return ticket

    def edit(
            self,
            edited_by: UUID,
            title: str | None = None,
            description: str | None = None,
            priority: TicketPriority | None = None,
            tags: list[Tag] | None = None
    ) -> None:
        """Редактирование тикета"""

        edited_fields = []

        # 1. Редактировать может только автор или инициатор
        if edited_by not in {self.reporter_id, self.created_by}:
            raise PermissionDeniedError("Only author or reporter can edit ticket")

        # 2. Нельзя редактировать тикет, если он в работе + если тикет архивирован
        if self.status not in ALLOWED_EDIT_STATUSES:
            raise InvariantViolationError("Cannot edit ticket in not allowed status")
        if self.is_deleted:
            raise InvariantViolationError("Cannot edit archived ticket")

        # 3. Редактирование заголовка
        if title is not None and title.strip() != self.title and title.strip():
            old_title = self.title
            self.title = title.strip()
            edited_fields.append(("title", old_title, self.title))

        # 4. Редактирование описания
        if description is not None and description.strip() != self.description \
                and description.strip():
            old_description = self.description
            self.description = description.strip()
            edited_fields.append(("description", old_description, self.description))

        # 5. Обновление приоритета
        if priority is not None and priority != self.priority:
            old_priority = self.priority
            self.priority = priority
            edited_fields.append(("priority", old_priority, self.priority))

            # 5.1 Регистрация доменного события при изменении приоритета
            self.register_event(
                TicketPriorityChanged(
                    ticket_id=self.id,
                    number=f"{self.number}",
                    changed_by=edited_by,
                    old_priority=old_priority,
                    new_priority=self.priority,
                )
            )

        # 6. Редактирование тегов
        if tags is not None and set(tags) != set(self.tags):
            old_tags = [tag.name for tag in self.tags]
            self.tags = tags[:]
            edited_fields.append(("tags", old_tags, [tag.name for tag in tags]))

        # 7. Запись изменений в историю
        if edited_fields:
            self.updated_at = current_datetime()
            for field, old_value, new_value in edited_fields:
                self.write_history(
                    actor_id=edited_by,
                    action=f"{field}_edited",
                    old_value=str(old_value),
                    new_value=str(new_value),
                    description="Поле отредактировано"
                )

    def archive(self, archived_by: UUID, archived_by_role: UserRole) -> None:
        """Архивирование тикета"""

        # 1. Проверка прав на архивирование
        is_creator_or_reporter = archived_by in {self.created_by, self.reporter_id}
        is_staff = archived_by_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}
        if not (is_creator_or_reporter or is_staff):
            raise PermissionDeniedError("Insufficient permissions to archive a ticket")

        if self.is_deleted:
            return

        # 2. Архивирование
        self.deleted_at = current_datetime()
        self.updated_at = current_datetime()

        # 3. Запись в историю
        self.write_history(
            actor_id=archived_by,
            action="ticket_archived",
            description="Тикет архивирован",
        )

        # 4. Регистрация доменного события
        self.register_event(
            TicketArchived(
                ticket_id=self.id,
                number=f"{self.number}",
                reporter_id=self.reporter_id,
                archived_by=archived_by,
            )
        )

    def assign_to(
            self,
            assignee_id: UUID,
            assignee_role: UserRole,
            assigned_by: UUID,
            assigned_by_role: UserRole,
    ) -> None:
        """Назначает (или переназначает) тикет на исполнителя (агента поддержки)"""

        # 1. Назначить тикет могут только внутренние сотрудники
        if assigned_by_role not in {
            UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN
        }:
            raise PermissionDeniedError("Only support team can assign tickets")

        # 2. Назначить тикет можно только на сотрудников поддержки
        if assignee_role not in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN}:
            raise PermissionDeniedError("Tickets can only be assigned to support team")

        # 3. Для назначения тикета должен быть определённый статус
        if self.status not in ALLOWED_ASSIGN_STATUSES:
            raise PermissionDeniedError(
                f"Cannot assign ticket in status '{self.status.value}'. "
                f"Allowed statuses: {', '.join(status for status in ALLOWED_ASSIGN_STATUSES)}"
            )

        # 4. Если тикет переназначается на самого себя - то без записи в историю
        if assignee_id == self.assigned_to:
            return

        # 5. Назначение исполнителя
        old_assignee = self.assigned_to
        self.assigned_to = assignee_id

        # 6. Запись изменений в историю
        self.write_history(
            actor_id=assigned_by,
            action="assigned",
            old_value=f"{old_assignee}" if old_assignee else None,
            new_value=f"{assignee_id}",
            description="Тикет назначен пользователю",
        )

        self.register_event(
            TicketAssigned(
                ticket_id=self.id,
                assignee_id=assignee_id,
                assigned_by=assigned_by,
                old_assignee=old_assignee,
            )
        )

    def _can_change_to_status(self, new_status: TicketStatus, role: UserRole) -> bool:
        """Проверка прав на конкретный переход статуса"""

        # 1. Системный администратор и менеджер могут всё
        if role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return True

        # 2. Переходя для агента поддержки
        if role == UserRole.SUPPORT_AGENT:
            if self.status == TicketStatus.PENDING_APPROVAL:
                return False  # Агент не может согласовывать
            return new_status in {
                TicketStatus.OPEN,
                TicketStatus.IN_PROGRESS,
                TicketStatus.WAITING,
                TicketStatus.RESOLVED,
                TicketStatus.CLOSED,
            }

        # 3. Администратор клиента может согласовывать свои тикеты
        if role == UserRole.CUSTOMER_ADMIN:
            if self.status == TicketStatus.PENDING_APPROVAL:
                return new_status in {TicketStatus.OPEN, TicketStatus.REJECTED}
            return new_status == TicketStatus.REOPENED

        # 4. Клиенты могут только переоткрывать закрытые тикеты
        if role == UserRole.CUSTOMER:
            return new_status == TicketStatus.REOPENED and self.status == TicketStatus.CLOSED

        return False

    def change_status(
            self, new_status: TicketStatus, changed_by: UUID, changed_by_role: UserRole
    ) -> None:
        """Изменение статуса"""

        # 1. Проверка возможности перехода к новому статусу
        if new_status not in ALLOWED_TRANSITIONS.get(self.status, []):
            raise PermissionDeniedError(
                f"Not allowed status transition: from '{self.status}' to '{new_status}'"
            )

        # 2. Проверка прав пользователя на данный переход
        if not self._can_change_to_status(new_status, changed_by_role):
            raise PermissionDeniedError(
                f"Role '{changed_by_role}' is not allowed to change status to '{new_status}'"
            )

        # 3. Установка нового статуса
        old_status = self.status
        self.status = new_status

        # 4. Если тикет закрыт, то устанавливается время закрытия
        if new_status == TicketStatus.CLOSED:
            self.closed_at = current_datetime()

        # 5. Запись изменений в историю
        self.write_history(
            actor_id=changed_by,
            action="status_changed",
            old_value=f"{old_status}",
            new_value=f"{new_status}",
            description=(
                f"Статус изменён с `{old_status.value}` на `{new_status.value}`"
            )
        )

    def write_history(
        self,
        actor_id: UUID,
        action: str,
        description: str,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> None:
        """
        Записывает событие в историю тикета.
        Используется из сервисного слоя и из внутренних методов.
        """

        self.history.append(
            TicketHistoryEntry(
                ticket_id=self.id,
                actor_id=actor_id,
                action=action,
                old_value=old_value,
                new_value=new_value,
                description=description,
            )
        )
