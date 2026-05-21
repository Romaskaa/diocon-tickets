from uuid import UUID

from fastapi import APIRouter, status

router = APIRouter(prefix="/categories", tags=["Категории"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=...,
    summary="Создать категорию"
)
async def create_category(): ...


@router.patch(
    path="/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=...,
    summary="Редактировать категорию"
)
async def edit_category(category_id: UUID): ...


@router.get(
    path="/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=...,
    summary="Получение категории"
)
async def get_category(category_id: UUID): ...


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=...,
    summary="Получение дерева категорий"
)
async def get_categories(): ...


@router.delete(
    path="/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=...,
    summary="Удалить категорию"
)
async def delete_category(category_id: UUID): ...
