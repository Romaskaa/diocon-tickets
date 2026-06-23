from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query

from src.shared.dependencies import PaginationDep, SessionDep
from src.shared.schemas import Page

from .domain.repos import ActivityLogRepository
from .infra.repos import SqlActivityLogRepository


def get_activity_log_repo(session: SessionDep) -> SqlActivityLogRepository:
    return SqlActivityLogRepository(session)


ActivityLogRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_log_repo)]


async def get_activity_logs_page(
        activity_log_repo: ActivityLogRepoDep,
        aggregate_type: str,
        aggregate_id: UUID,
        pagination: PaginationDep,
        actor_id: Annotated[
            UUID | None, Query(..., description="Тот кто выполнил действие")
        ] = None,
        action: Annotated[
            str | None, Query(..., description="Тип выполненного действия")
        ] = None,
) -> Page[...]:
    page = await activity_log_repo.get_for_aggregate(
        aggregate_type, aggregate_id, pagination=pagination, actor_id=actor_id, action=action
    )
    return page.to_response(...)


ActivityLogsPageDep = Annotated[Page[...], Depends(get_activity_logs_page)]
