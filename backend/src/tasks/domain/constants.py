from .vo import TaskStatus

# Возможные переходы между статусами задачи
ALLOWED_TRANSITIONS: dict[TaskStatus: list[TaskStatus]] = {
    TaskStatus.BACKLOG: [TaskStatus.TODO, TaskStatus.CANCELLED],
    TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED],
    TaskStatus.IN_PROGRESS: [
        TaskStatus.BLOCKED, TaskStatus.REVIEW, TaskStatus.DONE, TaskStatus.CANCELLED
    ],
    TaskStatus.BLOCKED: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
    TaskStatus.REVIEW: [TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELLED],
    TaskStatus.DONE: [],
    TaskStatus.CANCELLED: [],
}
