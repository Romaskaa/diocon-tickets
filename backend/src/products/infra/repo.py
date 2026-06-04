from typing import override

from sqlalchemy import String, cast, desc, func, select, text

from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ...shared.schemas import Page, PageParams
from ..domain.entities import SoftwareProduct
from ..domain.vo import ProductCategory, ProductStatus
from .models import SoftwareProductOrm


class SoftwareProductMapper(ModelMapper[SoftwareProduct, SoftwareProductOrm]):
    @staticmethod
    def to_entity(model: SoftwareProductOrm) -> SoftwareProduct:
        return SoftwareProduct(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            name=model.name,
            vendor=model.vendor,
            version=model.version,
            description=model.description,
            category=model.category,
            status=model.status,
            attributes=model.attributes,
            created_by=model.created_by,
            updated_by=model.updated_by,
        )

    @staticmethod
    def from_entity(entity: SoftwareProduct) -> SoftwareProductOrm:
        return SoftwareProductOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            name=entity.name,
            vendor=entity.vendor,
            version=entity.version,
            description=entity.description,
            category=entity.category,
            status=entity.status,
            attributes=entity.attributes,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )


class SqlProductRepository(SqlAlchemyRepository[SoftwareProduct, SoftwareProductOrm]):
    model = SoftwareProductOrm
    model_mapper = SoftwareProductMapper

    @override
    async def paginate(
            self,
            pagination: PageParams,
            category: ProductCategory | None = None,
            status: ProductStatus | None = None,
            search: str | None = None,
    ) -> Page[SoftwareProduct]:
        # 1. Базовый запрос на получение всех данных
        stmt = select(self.model).where(self.model.deleted_at.is_(None))

        # 2. Применение фильтров
        if category is not None:
            stmt = stmt.where(self.model.category == category)
        if status is not None:
            stmt = stmt.where(self.model.status == status)
        if search is not None:
            search_term = cast(search, String)
            trigram_condition = text(
                "(name % :search OR vendor % :search OR description % :search)"
            ).bindparams(search=search)
            stmt = stmt.where(trigram_condition).order_by(
                desc(func.similarity(self.model.name, search_term))
            )

        return await self._paginate(stmt, pagination)
