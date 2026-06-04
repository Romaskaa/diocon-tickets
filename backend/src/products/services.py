from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..iam.domain.exceptions import PermissionDeniedError
from ..iam.domain.vo import UserRole
from .domain.entities import SoftwareProduct
from .domain.repo import ProductRepository
from .domain.vo import ProductStatus
from .mappers import map_product_to_response
from .schemas import ProductCreate, ProductResponse, validate_product_attributes


class ProductService:
    def __init__(self, session: AsyncSession, repository: ProductRepository) -> None:
        self.session = session
        self.repository = repository

    async def create(
            self, data: ProductCreate, created_by: UUID, created_by_role: UserRole
    ) -> ProductResponse:
        """Создание программного продукта"""

        # 1. Проверка прав и валидация
        if not created_by_role.is_support():
            raise PermissionDeniedError("Only support staff can create products")

        if data.status not in {ProductStatus.ACTIVE, ProductStatus.BETA}:
            raise ValueError("Initial status must be active or beta")

        validate_product_attributes(data.category, data.attributes)

        # 2. Создание и сохранение продукта
        product = SoftwareProduct(
            name=data.name,
            vendor=data.vendor,
            version=data.version,
            description=data.description,
            category=data.category,
            status=data.status,
            attributes=data.attributes,
            created_by=created_by,
        )
        await self.repository.create(product)
        await self.session.commit()

        return map_product_to_response(product)
