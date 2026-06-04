from uuid import UUID

from ..tickets.domain.events import TicketCreated
from .domain.entities import Notification
from .domain.vo import NotificationType


class NotificationFactory:
    """Фабрика для создания уведомлений из доменных событий"""

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
                    "ticket_number": event.number,
                    "title": event.title,
                }
            ) for target in targets
        ]
