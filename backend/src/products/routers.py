from fastapi import APIRouter, Depends, status

from ..iam.dependencies import CurrentUserDep, require_role
from ..iam.domain.constants import SUPPORT_TEAM
from ..shared.dependencies import PageParamsDep
from ..shared.schemas import Page
from .dependencies import ProductFiltersDep, ProductRepoDep, ProductServiceDep
from .domain.vo import ProductCategory
from .mappers import map_product_to_response
from .schemas import (
    AttributesSchemaResponse,
    ProductCreate,
    ProductResponse,
    get_product_attributes_schema,
)

router = APIRouter(prefix="/products", tags=["Программные продукты"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductResponse,
    summary="Создание программного продукта",
    description="Создаёт новую запись в справочнике"
)
async def create_product(
        current_user: CurrentUserDep, data: ProductCreate, service: ProductServiceDep
) -> ProductResponse:
    return await service.create(
        data, created_by=current_user.user_id, created_by_role=current_user.role
    )


@router.get(
    path="/categories/{category}/attributes-schema",
    status_code=status.HTTP_200_OK,
    response_model=AttributesSchemaResponse,
    summary="Получение JSON схемы аттрибутов продукта"
)
def get_product_category_attributes_schema(category: ProductCategory) -> AttributesSchemaResponse:
    schema = get_product_attributes_schema(category)
    return AttributesSchemaResponse(category=category, schema=schema)


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[ProductResponse],
    dependencies=[Depends(require_role(*SUPPORT_TEAM))],
    summary="Получение программных продуктов",
)
async def get_products(
        pagination: PageParamsDep,
        filters: ProductFiltersDep,
        repository: ProductRepoDep,
) -> Page[ProductResponse]:
    page = await repository.paginate(
        pagination, category=filters.category, status=filters.status, search=filters.query
    )
    return page.to_response(map_product_to_response)
