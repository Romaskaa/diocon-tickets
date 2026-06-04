from enum import StrEnum


class NotificationType(StrEnum):
    """Типы уведомлений в системе"""

    TICKET_CREATED = "ticket_created"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    COMMENT_ADDED = "comment_added"
    SYSTEM = "system"


class ChannelType(StrEnum):
    """Каналы куда пользователи получают уведомление"""

    EMAIL = "email"
    IN_APP = "in_app"  # всплывающее уведомление в Web-приложении
