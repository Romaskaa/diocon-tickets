from uuid import UUID

from src.iam.domain.authz import PermissionResult, Subject
from src.iam.domain.vo import UserRole

from .entities import Ticket


class SameCounterpartyRule:
    """
    Клиент может работать только в рамках своего контрагента.
    """

    def __init__(self, subject: Subject, counterparty_id: UUID | None) -> None:
        self.subject = subject
        self.counterparty_id = counterparty_id

    def check(self) -> PermissionResult:
        if (
                self.subject.has_any_role(UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN)
                and self.subject.counterparty_id != self.counterparty_id
        ):
            return PermissionResult(False, "Customers can only work in their counterparty")

        return PermissionResult(True)


class IsTicketReporterRule:
    def __init__(self, subject: Subject, ticket: Ticket) -> None:
        self.subject = subject
        self.ticket = ticket

    def check(self) -> PermissionResult:
        if self.ticket.reporter_id != self.subject.id:
            return PermissionResult(False, "Required ticket reporter")

        return PermissionResult(True)


class IsTicketCreatorRule:
    def __init__(self, subject: Subject, ticket: Ticket) -> None:
        self.subject = subject
        self.ticket = ticket

    def check(self) -> PermissionResult:
        if self.ticket.created_by != self.subject.id:
            return PermissionResult(False, "Required ticket creator")

        return PermissionResult(True)
