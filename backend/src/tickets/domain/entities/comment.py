from typing import Self

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from ....iam.domain.exceptions import PermissionDeniedError
from ....iam.domain.services import PermissionResult
from ....iam.domain.vo import UserRole
from ....media.domain.entities import Attachment
from ....shared.domain.entities import Entity
from ....shared.domain.exceptions import InvariantViolationError
from ....shared.utils.time import current_datetime
from ..events import CommentAdded, CommentEdited, ReactionAdded
from ..vo import CommentType, ReactionType


@dataclass(kw_only=True)
class Reaction(Entity):
    """
    Реакция на комментарий
    """

    comment_id: UUID
    author_id: UUID
    reaction_type: ReactionType

    @classmethod
    def create(
            cls,
            comment_id: UUID,
            author_id: UUID,
            author_role: UserRole,
            reaction_type: ReactionType
    ) -> Self:
        """Создание реакции"""

        # 1. Клиенты не могут ставить реакцию в работе
        if author_role.is_customer() and reaction_type == ReactionType.IN_PROGRESS:
            raise PermissionDeniedError("Customers cannot set 'In Progress' reaction")

        # 2. Создание сущности и публикация события
        reaction = cls(comment_id=comment_id, author_id=author_id, reaction_type=reaction_type)

        reaction.register_event(
            ReactionAdded(
                comment_id=comment_id,
                author_id=author_id,
                reaction_type=reaction_type
            )
        )

        return reaction

    def toggle(self, new_type: ReactionType, author_id: UUID, author_role: UserRole) -> None:
        """Переключение реакции"""

        if self.reaction_type == new_type:
            return

        if self.author_id != author_id:
            raise PermissionDeniedError("Only author can toggle his reaction")

        if author_role.is_customer() and new_type == ReactionType.IN_PROGRESS:
            raise PermissionDeniedError("Customers cannot set 'In Progress' reaction")

        self.reaction_type = new_type
        self.updated_at = current_datetime()


@dataclass(kw_only=True)
class Comment(Entity):
    """
    Комментарий для тикета
    """

    ticket_id: UUID
    author_id: UUID
    author_role: UserRole
    text: str
    type: CommentType = field(default=CommentType.PUBLIC)
    attachments: list[Attachment] = field(default_factory=list)

    # Ответы на комментарии (вложенные комментарии)
    parent_comment_id: UUID | None = None
    reply_count: int = field(default=0)

    def __post_init__(self) -> None:
        # 1. Текст комментария я не может быть пустым
        if not self.text.strip():
            raise ValueError("Comment text cannot be empty")

    @property
    def is_reply(self) -> bool:
        """Является ли комментарий ответом на другой комментарий"""

        return self.parent_comment_id is not None

    def increment_reply_count(self) -> None:
        """Увеличение счётчика ответов на 1"""

        self.reply_count += 1

    def decrement_reply_count(self) -> None:
        """Уменьшение счётчика ответов на 1"""

        if self.reply_count > 0:
            self.reply_count -= 1

    @staticmethod
    def _can_create(author_role: UserRole, comment_type: CommentType) -> PermissionResult:
        """Есть ли права на создание комментария"""

        # 1. Клиенты могут оставлять только публичные комментарии
        if author_role.is_customer() and comment_type != CommentType.PUBLIC:
            return PermissionResult(False, "Customers can only post PUBLIC comments")

        return PermissionResult(True)

    @classmethod
    def create(
            cls,
            ticket_id: UUID,
            author_id: UUID,
            author_role: UserRole,
            text: str,
            comment_type: CommentType = CommentType.PUBLIC
    ) -> Self:
        """Оставить комментарий"""

        # 1. Клиенты могут оставлять только публичные комментарии
        result = cls._can_create(author_role, comment_type)
        if not result.allowed:
            raise PermissionDeniedError(result.reason)

        # 2. Сохранение комментария
        comment_id = uuid4()
        comment = Comment(
            id=comment_id,
            ticket_id=ticket_id,
            author_id=author_id,
            author_role=author_role,
            text=text.strip(),
            type=comment_type,
        )

        # 3. Регистрация доменного события
        comment.register_event(
            CommentAdded(
                ticket_id=ticket_id,
                comment_id=comment.id,
                author_id=author_id,
                author_role=author_role,
                comment_type=comment_type,
                is_public=comment_type == CommentType.PUBLIC,
            )
        )

        return comment

    def create_reply(
            self,
            author_id: UUID,
            author_role: UserRole,
            text: str,
            comment_type: CommentType = CommentType.PUBLIC,
    ) -> "Comment":
        """Создание ответа на комментарий"""

        # 1. Нельзя отвечать на удалённый комментарий
        if self.is_deleted:
            raise PermissionDeniedError("Can't reply to deleted comment")

        # 2. Клиенты могут оставлять только публичные комментарии
        result = self._can_create(author_role, comment_type)
        if not result.allowed:
            raise PermissionDeniedError(result.reason)

        # 3. Создание вложенного комментария и инкрементация счётчика ответов
        reply = Comment(
            ticket_id=self.ticket_id,
            author_id=author_id,
            author_role=author_role,
            text=text.strip(),
            type=comment_type,
            parent_comment_id=self.id,
        )
        self.increment_reply_count()

        # 4. Регистрация доменного события
        reply.register_event(
            CommentAdded(
                ticket_id=self.ticket_id,
                comment_id=reply.id,
                author_id=author_id,
                author_role=author_role,
                comment_type=comment_type,
                is_public=comment_type == CommentType.PUBLIC,
            )
        )

        return reply

    def edit(self, new_text: str, edited_by: UUID) -> None:
        """Редактирование комментария"""

        # 1. Нельзя редактировать удалённый комментарий
        if self.is_deleted:
            raise PermissionDeniedError("Can't edit deleted comment")

        # 2. Редактировать может только автор
        if edited_by != self.author_id:
            raise PermissionDeniedError("Only author can edit comment")

        # 3. Новый текст не может быть пустым
        if not new_text.strip():
            raise ValueError("Comment text cannot be empty")

        # 4. Обновление значений
        self.text = new_text
        self.updated_at = current_datetime()

        # 5. Регистрация доменного события
        self.register_event(
            CommentEdited(
                ticket_id=self.ticket_id,
                comment_id=self.id,
                edited_by=edited_by,
            )
        )

    def delete(self, deleted_by: UUID, deleted_by_role: UserRole) -> None:
        """Удаление комментария (Soft-delete метод)"""

        # 1. Нельзя удалить уже удалённый комментарий
        if self.is_deleted:
            raise InvariantViolationError("Comment is already deleted")

        # 2. Удалять комментарии может только фактический создатель или сотрудник поддержки
        if self.author_id != deleted_by and not deleted_by_role.is_support():
            raise PermissionDeniedError("Only author or support staff can delete comment")

        # 2. Изменение состояния
        self.deleted_at = current_datetime()
