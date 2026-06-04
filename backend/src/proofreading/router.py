from fastapi import APIRouter, Body, Depends, status

from ..iam.dependencies import get_current_user
from .infra import langtool
from .schemas import TextCheckResult

router = APIRouter(prefix="/proofreading", tags=["Коррекция текста"])


@router.post(
    path="/spell-check",
    status_code=status.HTTP_200_OK,
    response_model=TextCheckResult,
    dependencies=[Depends(get_current_user)],
    summary="Проверка и исправление ошибок в тексте"
)
def check_text_spells(text: str = Body(..., embed=True)) -> TextCheckResult:
    return langtool.check_text_spells(text)
