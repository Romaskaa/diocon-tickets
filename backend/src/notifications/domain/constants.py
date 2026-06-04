from .vo import NotificationType

# Настройки по умолчанию для новых пользователей
DEFAULT_PREFERENCES: dict[NotificationType, dict[str, bool]] = {
    NotificationType.TICKET_CREATED: {"email": True, "in_app": True},
    NotificationType.TICKET_ASSIGNED: {"email": True, "in_app": True},
    NotificationType.TICKET_STATUS_CHANGED: {"email": True, "in_app": True},
    NotificationType.COMMENT_ADDED: {"email": False, "in_app": True},
    NotificationType.SYSTEM: {"email": True, "in_app": True},
}
