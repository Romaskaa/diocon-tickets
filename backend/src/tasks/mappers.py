from ..media.mappers import map_attachment_to_response
from ..tickets.schemas import Tag
from .domain.entities import Task
from .domain.repos import TaskView
from .schemas import TaskResponse, TaskViewResponse


def map_task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        is_archived=task.is_deleted,
        project_id=task.project_id,
        ticket_id=task.ticket_id,
        number=task.number.value,
        title=task.title,
        description=task.description,
        priority=task.priority,
        story_points=None if task.story_points is None else task.story_points.value,
        status=task.status,
        assignee_id=task.assignee_id,
        reviewer_id=task.reviewer_id,
        estimated_hours=None if task.estimated_hours is None else float(task.estimated_hours),
        actual_hours=task.actual_hours,
        due_date=task.due_date,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_by=task.created_by,
        tags=[Tag(name=tag.name, color=tag.color) for tag in task.tags],
        attachments=[map_attachment_to_response(attachment) for attachment in task.attachments],
    )


def map_task_view_to_response(task: TaskView) -> TaskViewResponse:
    return TaskViewResponse(
        id=task.id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        number=task.number.value,
        title=task.title,
        status=task.status,
        priority=task.priority,
        assignee_id=task.assignee_id,
        due_date=task.due_date,
        story_points=task.story_points,
        project_id=task.project_id,
        ticket_id=task.ticket_id,
        tags=[Tag(name=tag.name, color=tag.color) for tag in task.tags],
    )
