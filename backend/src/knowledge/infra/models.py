from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...media.infra.models import AttachmentOrm

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import TEXT, Computed, DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ...core.settings import settings
from ..domain.vo import ArticleStatus, ArticleVisibility


class CategoryOrm(Base):
    __tablename__ = "categories"

    name: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    parent_category_id: Mapped[UUID | None] = mapped_column(nullable=True)


class ArticleVersionOrm(Base):
    __tablename__ = "article_versions"

    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), nullable=False)
    author_id: Mapped[UUID]
    number: Mapped[int]
    title: Mapped[str]
    content: Mapped[str] = mapped_column(TEXT)
    tags: Mapped[list[str]] = mapped_column(JSONB)

    attachments: Mapped[list["AttachmentOrm"]] = relationship(
        primaryjoin=(
            "and_(AttachmentOrm.owner_type=='article', "
            "foreign(AttachmentOrm.owner_id)==ArticleVersionOrm.id)"
        ),
        viewonly=True,
    )
    article: Mapped["ArticleOrm"] = relationship(back_populates="versions")
    chunks: Mapped[list["ArticleChunkOrm"]] = relationship(back_populates="version")

    __table_args__ = (
        UniqueConstraint("article_id", "number", name="uq_article_version_number"),
    )


class ArticleOrm(Base):
    __tablename__ = "articles"

    title: Mapped[str]
    content: Mapped[str]
    status: Mapped[ArticleStatus] = mapped_column(Enum(ArticleStatus))
    version_number: Mapped[int]

    product_id: Mapped[UUID | None] = mapped_column(nullable=True)
    category_id: Mapped[UUID | None] = mapped_column(nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB)

    author_id: Mapped[UUID]
    reviewer_id: Mapped[UUID | None] = mapped_column(nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    visibility: Mapped[ArticleVisibility] = mapped_column(Enum(ArticleVisibility))

    attachments: Mapped[list["AttachmentOrm"]] = relationship(
        secondary="article_versions",
        primaryjoin=(
            "and_("
            "ArticleOrm.id == foreign(ArticleVersionOrm.article_id), "
            "ArticleVersionOrm.number == ArticleOrm.version_number"
            ")"
        ),
        secondaryjoin=(
            "and_("
            "foreign(AttachmentOrm.owner_id) == ArticleVersionOrm.id, "
            "AttachmentOrm.owner_type == 'article'"
            ")"
        ),
        viewonly=True,
        lazy="select"
    )
    versions: Mapped[list["ArticleVersionOrm"]] = relationship(back_populates="article")


class ArticleChunkOrm(Base):
    __tablename__ = "article_chunks"

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("article_versions.id"), unique=False
    )
    # Ссылка на вложенный медиа контент
    attachment_id: Mapped[UUID | None] = mapped_column(nullable=True)

    content_type: Mapped[str]
    content: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    # Ембеддинг
    embedding: Mapped[list[float]] = mapped_column(VECTOR(settings.embeddings.dimensions))

    # Полнотекстовый вектор
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('russian', coalesce(content, ''))",
            persisted=True,
        ),
        nullable=True,
        index=False,
    )

    version: Mapped["ArticleVersionOrm"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_version_id", "version_id"),
        Index(
            "idx_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
        Index("idx_chunks_content_search_vector", "search_vector", postgresql_using="gin"),
    )
