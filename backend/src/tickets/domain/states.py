# ruff: noqa: ARG001, ARG002, ARG003, ARG004, RUF100, PLR6301
# ARG00* — unused method argument
# RUF100 — noqa directive

"""
Реализация State Pattern для управления переходами между состояниями.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import Ticket

import abc
from uuid import UUID

from src.shared.domain.exceptions import InvalidStateError

from .state_factory import register_state
from .vo import TicketStatus


class TicketState(abc.ABC):
    @property
    @abc.abstractmethod
    def status(self) -> TicketStatus: ...

    def edit(self, ticket: "Ticket", edited_by: UUID, **kwargs) -> None:
        raise InvalidStateError(f"Cannot edit ticket in status {self.status.value}")

    def assign(self, ticket: "Ticket", assignee_id: UUID, assigned_by: UUID) -> None:
        raise InvalidStateError(f"Cannot assign ticket in status {self.status.value}")

    def start_progress(self, ticket: "Ticket", started_by: UUID) -> None:
        raise InvalidStateError(f"Cannot start progress in status {self.status.value}")

    def resolve(self, ticket: "Ticket", resolved_by: UUID) -> None:
        raise InvalidStateError(f"Cannot resolve ticket in status {self.status.value}")

    def close(self, ticket: "Ticket", closed_by: UUID) -> None:
        raise InvalidStateError(f"Cannot close ticket in status {self.status.value}")

    def reopen(self, ticket: "Ticket", reopened_by: UUID) -> None:
        raise InvalidStateError(f"Cannot reopen ticket in status {self.status.value}")

    def cancel(self, ticket: "Ticket", cancelled_by: UUID) -> None:
        raise InvalidStateError(f"Cannot cancel ticket in status {self.status.value}")

    def reject(self, ticket: "Ticket", rejected_by: UUID) -> None:
        raise InvalidStateError(f"Cannot reject ticket in status {self.status.value}")


@register_state(TicketStatus.NEW)
class NewState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.NEW

    def assign(self, ticket: "Ticket", assignee_id: UUID, assigned_by: UUID) -> None:
        ticket.apply_assignment(assignee_id, assigned_by)
        ticket.transition_to(TicketStatus.OPEN, assigned_by)

    def edit(self, ticket: "Ticket", edited_by: UUID, **kwargs) -> None:
        pass

    def cancel(self, ticket: "Ticket", cancelled_by: UUID) -> None:
        ticket.clear_assignment()
        ticket.transition_to(TicketStatus.CANCELED, cancelled_by)


@register_state(TicketStatus.PENDING_APPROVAL)
class PendingApprovalState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.PENDING_APPROVAL

    def edit(self, ticket: "Ticket", edited_by: UUID, **kwargs) -> None:
        pass

    def assign(self, ticket: "Ticket", assignee_id: UUID, assigned_by: UUID) -> None:
        ticket.apply_assignment(assignee_id, assigned_by)
        ticket.transition_to(TicketStatus.OPEN, assigned_by)

    def reject(self, ticket: "Ticket", rejected_by: UUID) -> None:
        ticket.clear_assignment()
        ticket.transition_to(TicketStatus.REJECTED, rejected_by)


@register_state(TicketStatus.OPEN)
class OpenState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.OPEN

    def start_progress(self, ticket: "Ticket", started_by: UUID) -> None:
        ticket.transition_to(TicketStatus.IN_PROGRESS, started_by)

    def edit(self, ticket: "Ticket", edited_by: UUID, **kwargs) -> None:
        pass

    def assign(self, ticket: "Ticket", assignee_id: UUID, assigned_by: UUID) -> None:
        ticket.apply_assignment(assignee_id, assigned_by)
        ticket.transition_to(TicketStatus.OPEN, assigned_by)


@register_state(TicketStatus.IN_PROGRESS)
class InProgressState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.IN_PROGRESS

    def resolve(self, ticket: "Ticket", resolved_by: UUID) -> None:
        ticket.transition_to(TicketStatus.RESOLVED, resolved_by)

    def cancel(self, ticket: "Ticket", cancelled_by: UUID) -> None:
        ticket.clear_assignment()
        ticket.transition_to(TicketStatus.CANCELED, cancelled_by)


@register_state(TicketStatus.WAITING)
class WaitingState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.WAITING

    def start_progress(self, ticket: "Ticket", started_by: UUID) -> None:   # клиент ответил
        ticket.transition_to(TicketStatus.IN_PROGRESS, started_by)

    def resolve(self, ticket: "Ticket", resolved_by: UUID) -> None:
        ticket.transition_to(TicketStatus.RESOLVED, resolved_by)

    def edit(self, ticket: "Ticket", edited_by: UUID, **kwargs) -> None:
        pass


@register_state(TicketStatus.RESOLVED)
class ResolvedState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.RESOLVED

    def close(self, ticket: "Ticket", closed_by: UUID) -> None:
        ticket.mark_closed(closed_by)
        ticket.transition_to(TicketStatus.CLOSED, closed_by)

    def reopen(self, ticket: "Ticket", reopened_by: UUID) -> None:
        ticket.clear_closing()
        ticket.transition_to(TicketStatus.REOPENED, reopened_by)


@register_state(TicketStatus.CLOSED)
class ClosedState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.CLOSED

    def reopen(self, ticket: "Ticket", reopened_by: UUID) -> None:
        ticket.clear_closing()
        ticket.transition_to(TicketStatus.RESOLVED, reopened_by)


@register_state(TicketStatus.CANCELLED)
class CancelledState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.CANCELLED

    def reopen(self, ticket: "Ticket", reopened_by: UUID) -> None:
        ticket.transition_to(TicketStatus.OPEN, reopened_by)


@register_state(TicketStatus.REJECTED)
class RejectedState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.REJECTED

    def reopen(self, ticket: "Ticket", reopened_by: UUID) -> None:
        ticket.transition_to(TicketStatus.REOPENED, reopened_by)


@register_state(TicketStatus.REOPENED)
class ReopenedState(TicketState):
    @property
    def status(self) -> TicketStatus:
        return TicketStatus.REOPENED

    def start_progress(self, ticket: "Ticket", started_by: UUID) -> None:
        ticket.transition_to(TicketStatus.IN_PROGRESS, started_by)

    def resolve(self, ticket: "Ticket", resolved_by: UUID) -> None:
        ticket.transition_to(TicketStatus.RESOLVED, resolved_by)

    def edit(self, ticket: "Ticket", edited_by: UUID, **kwargs) -> None:
        pass

    def assign(self, ticket: "Ticket", assignee_id: UUID, assigned_by: UUID) -> None:
        ticket.apply_assignment(assignee_id, assigned_by)
        ticket.transition_to(TicketStatus.REOPENED, assigned_by)
