__all__ = ["router"]

from fastapi import APIRouter

from .projects import router as projects_router
from .tickets import router as tickets_router

router = APIRouter()  # noqa: RUF067

router.include_router(projects_router)  # noqa: RUF067
router.include_router(tickets_router)  # noqa: RUF067
