from uuid import UUID

from ...shared.domain.repo import Repository
from .entities import Article, ArticleVersion
from .vo import ArticleChunk, ArticleVisibility


class ArticleRepository(Repository[Article]):

    async def search(
            self,
            query: str,
            category_id: UUID | None = None,
            product_id: UUID | None = None,
            tags: list[str] | None = None,
            visibility: ArticleVisibility | None = None,
            *,
            top_k: int = 10,
            semantic_weight: float = 0.7,
            bm25_weight: float = 0.3,
    ) -> list[tuple[Article, float]]:
        """
        Гибридный поиск по тексту запроса.
        Возвращает список статей с релевантностью.
        """

    async def search_by_image(
            self,
            image_embedding: list[float],
            visibility: ArticleVisibility | None = None,
            *,
            top_k: int = 10,
    ) -> list[tuple[Article, float]]:
        """
        Поиск статей по релевантности изображения.
        Использует ембеддинг изображения для сравнения с чанками (content_type='image/*').
        """


class ArticleVersionRepository(Repository[ArticleVersion]):

    async def add_chunks(self, chunks: list[ArticleChunk]) -> None:
        """Сохранение проиндексированных чанков статей"""
