from .vo import CommentType, TicketStatus

# Разрешённые переходы между статусами тикета
ALLOWED_TRANSITIONS: dict[TicketStatus, list[TicketStatus]] = {
    TicketStatus.NEW: [TicketStatus.PENDING_APPROVAL, TicketStatus.OPEN],
    TicketStatus.PENDING_APPROVAL: [TicketStatus.OPEN, TicketStatus.REJECTED],
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS],
    TicketStatus.IN_PROGRESS: [TicketStatus.WAITING, TicketStatus.RESOLVED],
    TicketStatus.WAITING: [TicketStatus.IN_PROGRESS],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED],
    TicketStatus.CLOSED: [TicketStatus.REOPENED],
    TicketStatus.REOPENED: [TicketStatus.OPEN],
}

# Разрешённые статусы для назначения тикета
ALLOWED_ASSIGN_STATUSES: set[TicketStatus] = {
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING,
    TicketStatus.RESOLVED,
}

# Разрешённые статусы для редактирования тикета
ALLOWED_EDIT_STATUSES: set[TicketStatus] = {
    TicketStatus.NEW,
    TicketStatus.PENDING_APPROVAL,
}

# Статусы тикета при которых его нельзя комментировать
NON_COMMENTABLE_STATUSES: set[TicketStatus] = {
    TicketStatus.CLOSED, TicketStatus.REJECTED, TicketStatus.CANCELED,
}

# Человеко-читаемые типы комментариев (для UI)
COMMENT_TYPE_DISPLAY_NAMES: dict[CommentType, str] = {
    CommentType.INTERNAL: "Внутренний",
    CommentType.PUBLIC: "Публичный",
    CommentType.NOTE: "Личный (заметка)"
}
