__all__ = ["router"]

from fastapi import APIRouter

from .categories import router as category_router

router = APIRouter(prefix="/knowledge", tags=["База знаний"])

router.include_router(category_router)
