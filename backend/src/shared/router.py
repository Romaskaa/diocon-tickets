from typing import Annotated

from fastapi import APIRouter, Body, status

from .dependencies import SpellCheckerDep
from .infra.spellchecking import TextCheckResult

router = APIRouter(tags=["Общие утилиты"])


@router.post(
    path="/spellchecking",
    status_code=status.HTTP_200_OK,
    response_model=TextCheckResult,
    summary="Проверить ошибки в тексте"
)
def check_spelling(
        text: Annotated[str, Body(..., embed=True)], spell_checker: SpellCheckerDep
) -> TextCheckResult:
    return spell_checker.check(text)
