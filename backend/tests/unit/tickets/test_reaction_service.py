from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.tickets.domain.entities import Comment, Reaction
from src.tickets.domain.vo import ReactionType
from src.tickets.services import ReactionService


@pytest.fixture
def reaction_service(
        mock_session,
        mock_comment_repo,
        mock_reaction_repo,
        event_publisher,
):
    return ReactionService(
        session=mock_session,
        comment_repo=mock_comment_repo,
        reaction_repo=mock_reaction_repo,
        event_publisher=event_publisher,
    )


@pytest.fixture
def current_user():
    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.SUPPORT_AGENT,
        email="support.agent@example.com",
    )


@pytest.fixture
async def sample_comment(current_user, mock_comment_repo):
    comment = Comment.create(
        ticket_id=uuid4(),
        author_id=current_user.user_id,
        author_role=current_user.role,
        text="Тестовый комментарий"
    )
    await mock_comment_repo.create(comment)
    return comment


class TestToggle:
    """
    Тесты для переключения реакции
    """

    @pytest.fixture
    async def sample_reaction(self, sample_comment, current_user, mock_reaction_repo):
        reaction = Reaction.create(
            comment_id=sample_comment.id,
            author_id=current_user.user_id,
            author_role=current_user.role,
            reaction_type=ReactionType.IMPORTANT,
        )
        await mock_reaction_repo.create(reaction)
        return reaction

    @pytest.mark.asyncio
    async def test_create_new_reaction_when_none_exists(
            self, reaction_service, current_user, sample_comment, mock_session, mock_reaction_repo
    ):
        """
        Добавление новой реакции
        """

        await reaction_service.toggle(
            comment_id=sample_comment.id,
            current_user=current_user,
            reaction_type=ReactionType.LIKE,
        )

        mock_session.commit.assert_awaited_once()

        existing = await mock_reaction_repo.find(
            comment_id=sample_comment.id,
            author_id=current_user.user_id,
            reaction_type=ReactionType.LIKE,
        )

        assert existing is not None

    @pytest.mark.asyncio
    async def test_delete_reaction_when_same_type_clicked(
            self,
            reaction_service,
            current_user,
            sample_comment,
            sample_reaction,
            mock_session,
            mock_reaction_repo,
    ):
        """
        Реакция должна удалиться, если пользователь нажал на неё ещё раз
        """

        await reaction_service.toggle(
            comment_id=sample_comment.id,
            current_user=current_user,
            reaction_type=ReactionType.IMPORTANT,
        )

        mock_session.commit.assert_awaited_once()

        existing = await mock_reaction_repo.read(sample_reaction.id)

        assert existing is None

    @pytest.mark.asyncio
    async def test_change_reaction_type_when_different_clicked(
            self,
            reaction_service,
            current_user,
            sample_comment,
            sample_reaction,
            mock_session,
            mock_reaction_repo,
    ):
        """
        При нажатии на другую реакцию меняется тип
        """

        await reaction_service.toggle(
            comment_id=sample_comment.id,
            current_user=current_user,
            reaction_type=ReactionType.LIKE,
        )

        mock_session.commit.assert_awaited_once()

        existing = await mock_reaction_repo.read(sample_reaction.id)

        assert existing is not None
        assert existing.reaction_type == ReactionType.IMPORTANT
