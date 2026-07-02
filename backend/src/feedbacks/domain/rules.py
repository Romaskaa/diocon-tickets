from typing import ClassVar

from src.iam.domain.authz import PermissionResult, Subject
from src.iam.domain.vo import UserRole
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import TicketStatus

from .entities import Feedback


class IsCustomerRule:
    """
    Проверяет, что субъект является клиентом.
    """

    def __init__(self, subject: Subject) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        for role in self.subject.roles:
            if role.is_customer():
                return PermissionResult(True)
        
        return PermissionResult(False, "Only customer can leave feedback")
            

class IsSupportRule:
    """
    Проверяет, что субъект является сотрудником поддержики или администратором.
    """

    ALLOWED_ROLES: ClassVar[set[UserRole]] = {
        UserRole.SUPPORT_AGENT,
        UserRole.SUPPORT_MANAGER,
        UserRole.ADMIN,
    }

    def __init__(self, subject: Subject) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        for role in self.ALLOWED_ROLES:
            if self.subject.has_role(role):
                return PermissionResult(True)
            
        return PermissionResult(False, "Only support can view feedback list")
    

class IsTicketReporterRule:
    """
    Проверяет, что субъект является инициатором тикета.
    """

    def __init__(self, subject: Subject, ticket: Ticket) -> None:
        self.subject = subject
        self.ticket = ticket
    
    def check(self) -> PermissionResult:
        if self.subject.id == self.ticket.reporter_id:
            return PermissionResult(True)
        
        return PermissionResult(False, "Only ticket reporter can leave feedback")
    

class IsTicketClosedRule:
    """
    Проверяет, что тикет закрыт.
    """

    def __init__(self, ticket: Ticket) -> None:
        self.ticket = ticket

    def check(self) -> PermissionResult:
        if self.ticket.status == TicketStatus.CLOSED:
            return PermissionResult(True)

        return PermissionResult(False, "Feedback can be left only for closed tickets")
    

class IsFeedbackAuthorRule:
    """
    Проверяет, что субъект является автором отзыва.
    """

    def __init__(self, subject: Subject, feedback: Feedback) -> None:
        self.subject = subject
        self.feedback = feedback

    def check(self) -> PermissionResult:
        if self.subject.id == self.feedback.author_id:
            return PermissionResult(True)
        
        return PermissionResult(False, "Only feedback author can manage feedback")