from fastapi import APIRouter, Depends, status

from src.iam.dependencies import require_role
from src.iam.domain.vo import UserRole
from src.shared.schemas import Page

from .dependencies import ActivityLogsPageDep

router = APIRouter(prefix="/activity-logs", tags=["История действий"])


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[...],
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
    summary="Получить историю действий",
)
async def get_activity_logs(page: ActivityLogsPageDep): ...
