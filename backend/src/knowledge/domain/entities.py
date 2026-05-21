from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ...media.domain.entities import Attachment
from ...shared.domain.entities import AggregateRoot, Entity
from ...shared.domain.exceptions import InvalidStateError
from ...shared.utils.text import get_latin_slug
from ...shared.utils.time import current_datetime
from ..utils import estimate_reading_time
from .events import ArticleCreated, ArticleEdited, ArticlePublished
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
class ArticleVersion(Entity):
    """
    Версия статьи - для аудита и отката
    """

    article_id: UUID
    author_id: UUID

    # Порядковый номер версии
    number: int

    # Контент
    title: str
    content: str
    tags: list[str] = field(default_factory=list)

    attachments: list[Attachment] = field(default_factory=list)


@dataclass(kw_only=True)
class Article(AggregateRoot):
    """
    Статья базы знаний.
    Управляет: контентом, версиями, статусами, связями с тикетами/продуктами
    """

    title: str
    content: str
    status: ArticleStatus
    version_number: int = 0

    product_id: UUID | None = None
    category_id: UUID | None = None
    tags: list[str] = field(default_factory=list)

    # Авторство и публикация
    author_id: UUID
    reviewer_id: UUID | None = None
    published_at: datetime | None = None
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
            author_id: UUID,
            visibility: ArticleVisibility = ArticleVisibility.INTERNAL,
            tags: list[str] | None = None,
            product_id: UUID | None = None,
            category_id: UUID | None = None,
    ) -> "Article":
        """Создание статьи базы знаний"""

        article_id = uuid4()
        article = cls(
            id=article_id,
            title=title,
            content=content,
            tags=[] if tags is None else tags,
            status=ArticleStatus.DRAFT,
            author_id=author_id,
            product_id=product_id,
            category_id=category_id,
            visibility=visibility,
        )

        article.register_event(
            ArticleCreated(
                article_id=article_id,
                title=title,
                author_id=author_id,
            ),
        )

        return article

    def increment_version(self) -> None:
        """
        Инкрементация номера текущей версии.
        Метод должен вызываться из доменного сервиса при выпуске новой версии.
        """

        self.version_number += 1

    def submit_for_review(self, reviewer_id: UUID) -> None:
        """Отдать статью на ревью"""

        if self.status != ArticleStatus.DRAFT:
            raise InvalidStateError("Only draft articles can be submitted for review")

        self.status = ArticleStatus.IN_REVIEW
        self.reviewer_id = reviewer_id
        self.updated_at = current_datetime()

    def publish(self, published_by: UUID) -> None:
        """Публикация статьи"""

        if self.status != ArticleStatus.IN_REVIEW:
            raise InvalidStateError("Only review articles can be published")

        self.status = ArticleStatus.PUBLISHED
        self.published_at = current_datetime()
        self.updated_at = current_datetime()

        self.register_event(
            ArticlePublished(
                article_id=self.id,
                title=self.title,
                published_by=published_by,
                visibility=self.visibility,
            )
        )

    def change_visibility(self, visibility: ArticleVisibility) -> None:
        """Изменение области видимости статьи"""

        if self.visibility == visibility:
            return

        self.visibility = visibility
        self.updated_at = current_datetime()

    def edit(
            self,
            *,
            edited_by: UUID,
            title: str | None = None,
            content: str | None = None,
            tags: list[str] | None = None,
    ) -> None:
        """Редактирование содержимого статьи"""

        if self.status == ArticleStatus.ARCHIVED:
            raise InvalidStateError("Cannot edit archived article")

        is_edited = False

        if title is not None and title.strip() != self.title:
            self.title = title.strip()
            is_edited = True

        if content is not None and content.strip() != self.content:
            self.content = content.strip()
            is_edited = True

        if tags is not None and set(tags) != set(self.tags):
            self.tags = tags
            is_edited = True

        if is_edited:
            self.updated_at = current_datetime()

            self.register_event(
                ArticleEdited(
                    article_id=self.id,
                    title=self.title,
                    edited_by=edited_by,
                )
            )

    def apply_version(self, version: ArticleVersion) -> None:
        """Применение версии к текущей статье"""

        # 1. Версия должна принадлежать текущей статье
        if self.id != version.article_id:
            raise ValueError("Target version does not belong to this article")

        # 2. Нельзя накатить версию к архивированной статье
        if self.status == ArticleStatus.ARCHIVED:
            raise InvalidStateError("Cannot apply version for archived article")

        # 3. Применение изменений
        self.title = version.title
        self.content = version.content
        self.tags = version.tags
        self.version_number = version.number
