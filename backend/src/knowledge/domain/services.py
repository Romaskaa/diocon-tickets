from uuid import UUID

from .entities import Article, ArticleVersion
from .vo import ArticleVisibility


def compose_article(
        author_id: UUID,
        title: str,
        content: str,
        tags: list[str] | None = None,
        visibility: ArticleVisibility = ArticleVisibility.INTERNAL,
        product_id: UUID | None = None,
        category_id: UUID | None = None,
) -> tuple[Article, ArticleVersion]:
    """
    Создаёт новую статью и её первую версию.
    Возвращает кортеж (статья, начальная версия).
    """

    # 1. Создание статьи
    article = Article.create(
        author_id=author_id,
        title=title,
        content=content,
        tags=tags,
        product_id=product_id,
        category_id=category_id,
        visibility=visibility,
    )

    # 2. Выпуск первой версии
    article.increment_version()
    version = ArticleVersion(
        article_id=article.id,
        author_id=author_id,
        number=article.version_number,
        title=title,
        content=content,
        tags=tags,
        product_id=product_id,
        category_id=category_id,
    )

    return article, version


def revise_article(
        article: Article,
        *,
        edited_by: UUID,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
) -> ArticleVersion | None:
    """Редактирует статью базы знаний с созданием новой версии"""

    # 1. Получение времени последнего редактирования статьи
    last_updated_at = article.updated_at

    # 2. Редактирование статьи (вызов доменного метода)
    article.edit(
        edited_by=edited_by,
        title=title,
        content=content,
        tags=tags,
    )

    # 3. Создание новой версии, только при условии изменения состояния статьи
    if article.updated_at <= last_updated_at:
        return None

    # 3.1 Увеличение счётчика версий
    article.increment_version()

    return ArticleVersion(
        article_id=article.id,
        author_id=edited_by,
        number=article.version_number,
        title=title,
        content=content,
        tags=tags,
    )
