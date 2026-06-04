from typing import Any

from uuid import UUID

from sqlalchemy import TEXT, Computed, Enum, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from ...core.database import Base
from ..domain.vo import ProductCategory, ProductStatus


class SoftwareProductOrm(Base):
    __tablename__ = "software_products"

    name: Mapped[str]
    vendor: Mapped[str]
    category: Mapped[ProductCategory] = mapped_column(Enum(ProductCategory))
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    version: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus))

    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB)

    created_by: Mapped[UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(nullable=True)

    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            (
                "to_tsvector('russian', coalesce(name, '') || ' ' || "
                "coalesce(vendor, '') || ' ' || "
                "coalesce(description, '') || ' ' || "
                "coalesce(version, ''))"
            ),
            persisted=True,
        ),
        nullable=True,
    )

    __table_args__ = (
        # 1. GIN индекс для полнотекстового поиска (@@ оператор)
        Index("ix_software_products_search", "search_vector", postgresql_using="gin"),

        # 2. GIN индекс для структурного поиска по JSONB (@>, ?, ?| операторы)
        Index("ix_software_products_attributes", "attributes", postgresql_using="gin"),

        # 3. Частичный индекс: только активные продукты (ускоряет 90% запросов)
        Index(
            "ix_software_products_active",
            "category",
            "name",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )
