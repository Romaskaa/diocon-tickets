from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from ...media.domain.entities import Attachment
from ...shared.domain.entities import Entity
from ...shared.utils.text import get_latin_slug
from ...shared.utils.time import current_datetime
from ..utils import estimate_reading_time
from .vo import ArticleStatus, ArticleVisibility


@dataclass(kw_only=True)
class Category(Entity):
    """
    Категория статьи базы знаний (папка для хранения статей)
    """

    name: str
    slug: str
    description: str | None = None
    parent_category_id: UUID | None = None

    def __post_init__(self) -> None:
        # Наименование и описание не может быть пустым
        if not self.name.strip() or \
                (self.description is not None and not self.description.strip()):
            raise ValueError("Category name or description cannot be empty")

    @classmethod
    def create(
            cls,
            name: str,
            description: str | None = None,
            parent_category_id: UUID | None = None,
    ) -> "Category":
        """Создание категории базы знаний"""

        slug = get_latin_slug(name)
        return cls(
            name=name,
            slug=slug,
            description=description,
            parent_category_id=parent_category_id,
        )

    def archive(self) -> None:
        """Архивирование категории"""

        if self.is_deleted:
            return

        self.deleted_at = current_datetime()


@dataclass(kw_only=True)
class Article(Entity):
    """
    Версия статьи - для аудита и отката
    """

    # Единый ID для разных версий
    article_id: UUID

    # Контент
    title: str
    content: str
    tags: list[str] = field(default_factory=list)

    # Ссылки на другие сущности
    category_id: UUID | None = None
    product_id: UUID | None = None

    # Номер версии
    version: int = 1

    # Авторство и публикация
    author_id: UUID
    reviewer_id: UUID | None = None
    published_at: datetime | None = None

    # Статус и видимость
    status: ArticleStatus
    visibility: ArticleVisibility

    attachments: list[Attachment] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Заголовок и описание не могут быть пустыми
        if not self.title.strip() or not self.content.strip():
            raise ValueError("Article title or content cannot be empty")

    @property
    def reading_time_minutes(self) -> int:
        """Время прочтения статьи в минутах"""

        return estimate_reading_time(self.content)

    @classmethod
    def create(
            cls,
            title: str,
            content: str,
            created_by: UUID,
            visibility: ArticleVisibility = ArticleVisibility.INTERNAL,
            tags: list[str] | None = None,
    ) -> "Article":
        ...
