from typing import Annotated, Self

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from typing_extensions import Doc

from src.iam.domain.vo import UserRole
from src.media.domain.entities import Attachment
from src.shared.domain.entities import AggregateRoot
from src.shared.domain.exceptions import InvariantViolationError
from src.shared.utils.time import current_datetime

from ..events import (
    TicketArchived,
    TicketAssigned,
    TicketClosed,
    TicketCreated,
    TicketPriorityChanged,
    TicketReopened,
    TicketResolved,
    TicketStatusChanged,
)
from ..state_factory import get_state
from ..states import TicketState
from ..vo import (
    Priority,
    Tag,
    TicketNumber,
    TicketStatus,
    TicketType,
)


@dataclass(kw_only=True)
class Ticket(AggregateRoot):
    """
    Заявка - запрос на услугу от пользователя.
    """

    project_id: UUID | None = None
    counterparty_id: UUID | None = None
    product_id: UUID | None = None

    created_by: Annotated[UUID, Doc("Фактический создатель заявки")]
    created_by_role: UserRole
    reporter_id: Annotated[UUID, Doc("Инициатор/автор проблемы (тот кто пожаловался)")]

    number: TicketNumber
    title: str
    description: str
    type: TicketType
    status: TicketStatus
    priority: Priority
    assignee_id: Annotated[UUID | None, Doc("Исполнитель")] = None
    closed_at: datetime | None = None

    tags: list[Tag] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)

    def __post_init__(self) -> None:
        # 1. Заголовок не должен быть пустым
        if not self.title.strip():
            raise ValueError("Title cannot be empty")

        # 2. если тикет создан клиентом - контрагент должен быть заполнен
        if self.created_by_role.is_customer and self.counterparty_id is None:
            raise InvariantViolationError(
                "Customer-created ticket must be linked to a counterparty"
            )

    @property
    def state(self) -> TicketState:
        """
        Текущее состояние заявки.
        """

        return get_state(self.status)

    def transition_to(self, new_status: TicketStatus, actor_id: UUID) -> None:
        """
        Переход между состояниями тикета.
        """

        old_status = self.status
        self.status = new_status
        self.updated_at = current_datetime()

        self.register_event(
            TicketStatusChanged(
                ticket_id=self.id,
                old_status=old_status,
                new_status=self.status,
                changed_by=actor_id,
            )
        )

    # ====================== Публичное API ======================

    @classmethod
    def create(
        cls,
        number: TicketNumber,
        reporter_id: UUID,
        created_by: UUID,
        created_by_role: UserRole,
        title: str,
        description: str | None = None,
        ticket_type: TicketType = TicketType.SERVICE_REQUEST,
        priority: Priority = Priority.MEDIUM,
        project_id: UUID | None = None,
        counterparty_id: UUID | None = None,
        product_id: UUID | None = None,
        tags: list[Tag] | None = None,
    ) -> Self:

        initial_status = (
            TicketStatus.PENDING_APPROVAL if created_by_role.is_customer else TicketStatus.NEW
        )
        ticket = cls(
            created_by_role=created_by_role,
            created_by=created_by,
            reporter_id=reporter_id,
            number=number,
            title=title,
            description=description,
            type=ticket_type,
            priority=priority,
            status=initial_status,
            project_id=project_id,
            counterparty_id=counterparty_id,
            product_id=product_id,
            tags=tags if tags is not None else [],
        )

        ticket.register_event(
            TicketCreated(
                ticket_id=ticket.id,
                title=title,
                number=number,
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
        priority: Priority | None = None,
        tags: list[Tag] | None = None,
    ) -> None:
        """
        Отредактировать информацию и тикете.
        """

        self.state.edit(self, edited_by)

        changed = False

        if title is not None and title.strip() and title.strip() != self.title:
            self.title = title.strip()
            changed = True

        if description is not None and description.strip() != self.description:
            self.description = description.strip()
            changed = True

        if priority is not None and priority != self.priority:
            old_priority = self.priority
            self.priority = priority
            changed = True

            self.register_event(
                TicketPriorityChanged(
                    ticket_id=self.id,
                    number=self.number,
                    changed_by=edited_by,
                    old_priority=old_priority,
                    new_priority=self.priority,
                )
            )

        if tags is not None and set(tags) != set(self.tags):
            self.tags = tags[:]
            changed = True

        if changed:
            self.updated_at = current_datetime()

    def archive(self, archived_by: UUID) -> None:
        """
        Заархивировать тикет (мягкое удаление).
        """

        if self.is_deleted:
            return

        self.deleted_at = current_datetime()
        self.updated_at = current_datetime()

        self.register_event(
            TicketArchived(
                ticket_id=self.id,
                number=self.number,
                reporter_id=self.reporter_id,
                archived_by=archived_by,
            )
        )

    def assign(self, assignee_id: UUID, assigned_by: UUID) -> None:
        """
        Назначить тикет на исполнителя.
        """

        self.state.assign(self, assignee_id, assigned_by)

    def start_progress(self, started_by: UUID) -> None:
        """
        Начать работу над заявкой.
        """

        self.state.start_progress(self, started_by)

    def resolve(self, resolved_by: UUID) -> None:
        self.state.resolve(self, resolved_by)

        self.register_event(
            TicketResolved(
                ticket_id=self.id,
                number=self.number,
                resolved_by=resolved_by,
            )
        )

    def reopen(self, reopened_by: UUID) -> None:
        """
        Переоткрыть тикет.
        Сценарий использования: по решённой заявке возникла ошибка.
        """

        self.state.reopen(self, reopened_by)

        self.register_event(
            TicketReopened(
                ticket_id=self.id,
                number=self.number,
                reopened_by=reopened_by,
            )
        )

    def cancel(self, cancelled_by: UUID) -> None:
        """
        Отменить тикет.
        """

        self.state.cancel(self, cancelled_by)

    def reject(self, rejected_by: UUID) -> None:
        """
        Отклонить тикет. Например, клиент может отклонить на этапе согласования.
        """

        self.state.reject(self, rejected_by)

    def close(self, closed_by: UUID) -> None:
        """
        Закрыть тикет (заявка считается решённой после успешного решения
        и согласования с клиентом).
        """

        self.state.close(self, closed_by)

    # ====================== Внутренние мутации ======================

    def apply_assignment(self, assignee_id: UUID, assigned_by: UUID) -> None:
        """
        Устанавливает исполнителя + регистрирует событие.
        """

        if self.assignee_id == assignee_id:
            return

        old_assignee = self.assignee_id
        self.assignee_id = assignee_id

        self.register_event(
            TicketAssigned(
                ticket_id=self.id,
                number=self.number,
                title=self.title,
                assignee_id=assignee_id,
                assigned_by=assigned_by,
                old_assignee=old_assignee,
            )
        )

    def clear_assignment(self) -> None:
        """
        Сбрасывает текущего исполнителя (просто мутация данных).
        """

        self.assignee_id = None

    def mark_closed(self, closed_by: UUID) -> None:
        """
        Установить время закрытия тикета.
        """

        self.closed_at = current_datetime()

        self.register_event(
            TicketClosed(
                ticket_id=self.id,
                number=self.number,
                closed_by=closed_by,
            )
        )

    def clear_closing(self) -> None:
        """
        Сбросить время завершения (просто мутация данных).
        """

        self.closed_at = None
