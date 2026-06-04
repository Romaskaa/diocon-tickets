from typing import override

from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from .entities import SoftwareProduct
from .vo import ProductCategory, ProductStatus


class ProductRepository(Repository[SoftwareProduct]):

    @override
    async def paginate(
            self,
            pagination: PageParams,
            category: ProductCategory | None = None,
            status: ProductStatus | None = None,
            search: str | None = None,
    ) -> Page[SoftwareProduct]:
        """
        Поиск продуктов используя дополнительные параметры и пагинацию
        """
