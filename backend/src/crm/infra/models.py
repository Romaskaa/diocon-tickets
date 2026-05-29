from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ...iam.infra.models import UserOrm

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ..domain.vo import CounterpartyType


class CounterpartyOrm(Base):
    __tablename__ = "counterparties"

    counterparty_type: Mapped[CounterpartyType] = mapped_column(Enum(CounterpartyType))
    name: Mapped[str]
    legal_name: Mapped[str]
    inn: Mapped[str]
    kpp: Mapped[str | None] = mapped_column(nullable=True)
    okpo: Mapped[str | None] = mapped_column(nullable=True)
    phone: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    address: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(nullable=True)
    contact_persons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    is_active: Mapped[bool]

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("counterparties.id"), nullable=True, unique=False
    )

    head: Mapped[Optional["CounterpartyOrm"]] = relationship(
        remote_side="CounterpartyOrm.id", back_populates="branches",
    )
    branches: Mapped[list["CounterpartyOrm"]] = relationship(
        back_populates="head", cascade="all, delete-orphan"
    )

    customers: Mapped[list["UserOrm"]] = relationship(back_populates="counterparty")
    products: Mapped[list["CounterpartyProductOrm"]] = relationship(
        back_populates="counterparty"
    )

    __table_args__ = (
        # B-Tree индекс для быстрого поиска по Инн (по префиксу или постфиксу)
        Index("ix_counterparties_inn_btree", "inn"),
        # Полнотекстовый поиск по наименованиям
        Index(
            "ix_counterparties_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_counterparties_legal_name_trgm",
            "legal_name",
            postgresql_using="gin",
            postgresql_ops={"legal_name": "gin_trgm_ops"},
        ),
    )


class CounterpartyProductOrm(Base):
    __tablename__ = "counterparty_products"

    counterparty_id: Mapped[UUID] = mapped_column(ForeignKey("counterparties.id"), unique=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("software_products.id"), unique=False)

    counterparty: Mapped["CounterpartyOrm"] = relationship(back_populates="products")
