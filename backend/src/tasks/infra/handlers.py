from faststream.rabbit import RabbitQueue
from faststream.rabbit.fastapi import Logger, RabbitRouter

from ...timetracking.domain.events import WorklogApproved
from ..dependencies import TaskServiceDep

router = RabbitRouter()


@router.subscriber(queue=RabbitQueue("worklogs.approve", durable=True))
async def on_worklog_approved(
        event: WorklogApproved, service: TaskServiceDep, logger: Logger
) -> None:
    if event.task_id is None:
        logger.info("Task is not specified for worklog with ID - '%s'", event.worklog_id)
        return

    await service.add_actual_hours(task_id=event.task_id, hours=event.hours_spent)
