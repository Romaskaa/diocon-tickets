from .vo import TaskStatus

# Возможные переходы между статусами задачи
ALLOWED_STATUS_TRANSITIONS: dict[TaskStatus: set[TaskStatus]] = {
    TaskStatus.BACKLOG: {
        TaskStatus.TODO,
        TaskStatus.CANCELLED
    },

    TaskStatus.TODO: {
        TaskStatus.BACKLOG,
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED
    },

    TaskStatus.IN_PROGRESS: {
        TaskStatus.BACKLOG,
        TaskStatus.TODO,
        TaskStatus.PAUSED,
        TaskStatus.BLOCKED,
        TaskStatus.TO_REVIEW,
        TaskStatus.TO_FIX,
        TaskStatus.TO_TEST,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    },

    TaskStatus.PAUSED: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.CANCELLED,
    },

    TaskStatus.BLOCKED: {
        TaskStatus.BACKLOG,
        TaskStatus.TODO,
        TaskStatus.IN_PROGRESS,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
    },

    TaskStatus.TO_REVIEW: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.TO_FIX,
        TaskStatus.TO_TEST,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    },

    TaskStatus.TO_FIX: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.TO_REVIEW,
        TaskStatus.CANCELLED,
    },

    TaskStatus.TO_TEST: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.TO_REVIEW,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    },

    TaskStatus.DONE: {
        TaskStatus.CANCELLED,
        TaskStatus.TO_REVIEW,
        TaskStatus.TO_FIX,
        TaskStatus.IN_PROGRESS
    },
    TaskStatus.CANCELLED: {TaskStatus.BACKLOG, TaskStatus.TODO},
}

# Разрешённые статусы для редактирования задачи
ALLOWED_EDIT_STATUSES: set[TaskStatus] = {
    TaskStatus.BACKLOG, TaskStatus.TODO,
}

# Разрешённые статусы для назначения задачи
ALLOWED_ASSIGN_STATUSES: set[TaskStatus] = {
    TaskStatus.BACKLOG,
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.BLOCKED,
    TaskStatus.TO_REVIEW,
}

# Маппинг статусов задач в русские представления для UI
TASK_STATUS_LABEL_MAP: dict[TaskStatus, str] = {
    TaskStatus.BACKLOG: "В резерве",
    TaskStatus.TODO: "Готово к выполнению",
    TaskStatus.IN_PROGRESS: "В работе",
    TaskStatus.TO_REVIEW: "На проверке",
    TaskStatus.PAUSED: "На паузе",
    TaskStatus.BLOCKED: "Приостановлено",
    TaskStatus.DONE: "Выполнено",
    TaskStatus.CANCELLED: "Отменено",
}
