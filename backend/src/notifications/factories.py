from uuid import UUID

from src.core.settings import settings
from src.tickets.domain.events import TicketAssigned, TicketCreated

from .domain.entities import Notification
from .domain.vo import NotificationType


class NotificationFactory:
    """Фабрика для создания уведомлений из доменных событий."""

    @staticmethod
    def from_ticket_created(event: TicketCreated, targets: list[UUID]) -> list[Notification]:
        return [
            Notification(
                user_id=target,
                title="Тикет успешно создан",
                message=f"Тикет #{event.number} «{event.title}» был создан.",
                type=NotificationType.TICKET_CREATED,
                data={
                    "ticket_id": f"{event.ticket_id}",
                    "number": event.number,
                    "title": event.title,
                    "ticket_title": event.title,
                    "ticket_url": f"{settings.frontend_url}/tickets/{event.number}",
                    "app_name": settings.app.name,
                    "support_email": settings.mail.support_email,
                },
            )
            for target in targets
        ]

    @staticmethod
    def from_ticket_assigned(event: TicketAssigned, targets: list[UUID]) -> list[Notification]:
        action = "назначен" if event.old_assignee is None else "переназначен"

        return [
            Notification(
                user_id=target,
                title=f"Тикет {action}",
                message=f"Тикет #{event.number} «{event.title}» был {action}.",
                type=NotificationType.TICKET_ASSIGNED,
                data={
                    "ticket_id": f"{event.ticket_id}",
                    "number": event.number,
                    "title": event.title,
                    "ticket_title": event.title,
                    "ticket_url": f"{settings.frontend_url}/tickets/{event.number}",
                    "assigned_by": f"{event.assigned_by}",
                    "assignee_id": f"{event.assignee_id}",
                    "old_assignee": (
                        None if event.old_assignee is None else f"{event.old_assignee}"
                    ),
                    "app_name": settings.app.name,
                    "support_email": settings.mail.support_email,
                },
            )
            for target in targets
        ]
