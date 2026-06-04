from typing import Annotated

from fastapi import Depends, Query

from ..shared.dependencies import SessionDep
from .domain.repo import ProductRepository
from .domain.vo import ProductCategory, ProductStatus
from .infra.repo import SqlProductRepository
from .schemas import ProductFilters
from .services import ProductService


def get_product_repo(session: SessionDep) -> ProductRepository:
    return SqlProductRepository(session)


ProductRepoDep = Annotated[ProductRepository, Depends(get_product_repo)]


def get_product_service(session: SessionDep, repository: ProductRepoDep) -> ProductService:
    return ProductService(session, repository)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


def get_product_filters(
        category: Annotated[
            ProductCategory | None, Query(..., description="По категории")
        ] = None,
        status: Annotated[
            ProductStatus | None, Query(..., description="По статусу")
        ] = None,
        query: Annotated[
            str | None, Query(..., description="Полнотекстовый поиск")
        ] = None,
) -> ProductFilters:
    return ProductFilters(category=category, status=status, query=query)


ProductFiltersDep = Annotated[ProductFilters, Depends(get_product_filters)]
