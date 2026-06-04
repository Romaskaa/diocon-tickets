from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvariantViolationError
from src.shared.utils.time import current_datetime
from src.tickets.domain.entities import Comment
from src.tickets.domain.vo import CommentType


@pytest.fixture
def author_id():
    return uuid4()


@pytest.fixture
def ticket_id():
    return uuid4()


@pytest.fixture
def sample_public_comment(author_id, ticket_id):
    return Comment(
        ticket_id=ticket_id,
        author_id=author_id,
        author_role=UserRole.SUPPORT_AGENT,
        text="Публичный комментарий",
        type=CommentType.PUBLIC,
    )


def test_comment_text_cannot_be_empty():
    with pytest.raises(ValueError, match="text cannot be empty"):
        Comment.create(
            ticket_id=uuid4(),
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_AGENT,
            text="           ",
            comment_type=CommentType.PUBLIC,
        )


class TestCreate:
    """
    Тесты для создания комментария
    """

    @pytest.mark.parametrize(
        "comment_type", [CommentType.PUBLIC, CommentType.NOTE, CommentType.INTERNAL]
    )
    def test_support_create_all_comment_types_success(self, comment_type):
        """
        Сотрудник поддержки может оставлять любые типы комментариев
        """

        ticket_id = uuid4()
        comment = Comment.create(
            ticket_id=ticket_id,
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_AGENT,
            text="Тестовый комментарий",
            comment_type=comment_type,
        )

        assert comment.ticket_id == ticket_id

    @pytest.mark.parametrize("comment_type", [CommentType.INTERNAL, CommentType.NOTE])
    def test_customer_create_not_public_failed(self, comment_type):
        """
        Клиент может оставлять только публичные комментарии
        """

        with pytest.raises(PermissionDeniedError, match="can only post PUBLIC comments"):
            Comment.create(
                ticket_id=uuid4(),
                author_id=uuid4(),
                author_role=UserRole.CUSTOMER_ADMIN,
                text="Какой-то комментарий",
                comment_type=comment_type,
            )

    def test_customer_create_public_success(self):
        """
        Клиент успешно оставил публичный комментарий
        """

        ticket_id = uuid4()
        comment = Comment.create(
            ticket_id=ticket_id,
            author_id=uuid4(),
            author_role=UserRole.CUSTOMER,
            text="Тестовый комментарий",
            comment_type=CommentType.PUBLIC,
        )

        assert comment.ticket_id == ticket_id


class TestEdit:
    """
    Тестирование редактирования комментария
    """

    def test_edit_by_author_success(self, author_id, sample_public_comment):
        """
        Автор может успешно редактировать комментарий
        """

        sample_public_comment.edit(new_text="Новый текст", edited_by=author_id)

        assert sample_public_comment.updated_at != sample_public_comment.created_at

    def test_cannot_edit_by_not_author(self, sample_public_comment):
        """
        Только автор может редактировать свой комментарий
        """

        with pytest.raises(PermissionDeniedError, match="Only author can edit comment"):
            sample_public_comment.edit(new_text="Новый текст", edited_by=uuid4())

    def test_edit_to_empty_text(self, author_id, sample_public_comment):
        """
        Нельзя изменять содержание на пустой текст
        """

        with pytest.raises(ValueError, match="text cannot be empty"):
            sample_public_comment.edit(new_text="   ", edited_by=author_id)

    def test_edit_deleted_failed(self, author_id, sample_public_comment):
        """
        Нельзя редактировать удалённый комментарий
        """

        sample_public_comment.deleted_at = current_datetime()

        with pytest.raises(PermissionDeniedError, match="Can't edit deleted comment"):
            sample_public_comment.edit(new_text="Новый текст", edited_by=author_id)


class TestDelete:
    """
    Тестирование удаления комментария
    """

    def test_delete_by_author_success(self, author_id, sample_public_comment):
        """Успешное удаление комментария автором"""

        sample_public_comment.delete(deleted_by=author_id, deleted_by_role=UserRole.CUSTOMER)

        assert sample_public_comment.deleted_at is not None
        assert sample_public_comment.is_deleted is True

    def test_delete_by_support_staff_success(self, sample_public_comment):
        """
        Успешное удаление комментария сотрудником поддержки
        """

        sample_public_comment.delete(deleted_by=uuid4(), deleted_by_role=UserRole.SUPPORT_AGENT)

        assert sample_public_comment.deleted_at is not None
        assert sample_public_comment.is_deleted is True

    def test_delete_by_not_support_staff_or_author_failed(self, sample_public_comment):
        """
        Комментарий может удалить только автор или сотрудник поддержки
        """

        with pytest.raises(
                PermissionDeniedError, match="Only author or support staff can delete comment"
        ):
            sample_public_comment.delete(deleted_by=uuid4(), deleted_by_role=UserRole.CUSTOMER)

    def test_cannot_delete_already_deleted(self, author_id, sample_public_comment):
        """
        Нельзя удалить уже удалённый комментарий
        """

        sample_public_comment.delete(deleted_by=author_id, deleted_by_role=UserRole.SUPPORT_AGENT)

        assert sample_public_comment.is_deleted is True

        with pytest.raises(InvariantViolationError, match="Comment is already deleted"):
            sample_public_comment.delete(
                deleted_by=uuid4(), deleted_by_role=UserRole.SUPPORT_MANAGER
            )


class TestCreateReply:
    """
    Тестирование создание ответа на комментарий
    """

    @pytest.mark.parametrize(
        "comment_type", [CommentType.PUBLIC, CommentType.NOTE, CommentType.INTERNAL]
    )
    def test_support_staff_create_any_types_success(self, comment_type, sample_public_comment):
        """
        Сотрудник поддержки может создавать ответы с любым типом
        """

        author_id = uuid4()
        reply = sample_public_comment.create_reply(
            author_id=author_id,
            author_role=UserRole.SUPPORT_AGENT,
            text="Ответ на комментарий ",
            comment_type=comment_type,
        )
        excepted_reply_count = 1

        assert reply.author_id == author_id
        assert reply.parent_comment_id == sample_public_comment.id
        assert sample_public_comment.reply_count == excepted_reply_count
        assert reply.text == "Ответ на комментарий"

    def test_reply_to_deleted_comment_failed(self, author_id, sample_public_comment):
        """
        Нельзя ответить на удалённый комментарий
        """

        sample_public_comment.delete(
            deleted_by=author_id, deleted_by_role=UserRole.SUPPORT_MANAGER
        )

        with pytest.raises(PermissionDeniedError, match="Can't reply to deleted comment"):
            sample_public_comment.create_reply(
                author_id=uuid4(),
                author_role=UserRole.SUPPORT_AGENT,
                text="Ответ на комментарий",
            )
