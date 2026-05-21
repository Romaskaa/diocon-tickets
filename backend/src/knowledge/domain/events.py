from dataclasses import dataclass
from uuid import UUID

from ...shared.domain.events import Event
from .vo import ArticleVisibility


@dataclass(frozen=True, kw_only=True)
class ArticleCreated(Event):
    """Статья создана"""

    article_id: UUID
    author_id: UUID
    title: str


@dataclass(frozen=True, kw_only=True)
class ArticlePublished(Event):
    """Статья опубликована"""

    article_id: UUID
    title: str
    visibility: ArticleVisibility
    published_by: UUID


@dataclass(frozen=True, kw_only=True)
class ArticleEdited(Event):
    """Статья отредактирована"""

    article_id: UUID
    title: str
    edited_by: UUID
