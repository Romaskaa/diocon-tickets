from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.tickets.domain.entities import Reaction
from src.tickets.domain.vo import ReactionType


@pytest.fixture
def sample_reaction():
    return Reaction.create(
        comment_id=uuid4(),
        author_id=uuid4(),
        author_role=UserRole.SUPPORT_AGENT,
        reaction_type=ReactionType.LIKE,
    )


@pytest.mark.parametrize("reaction_type", list(ReactionType))
def test_support_create_any_reaction_success(reaction_type):
    """
    Сотрудник поддержки может создавать реакции с любым типом
    """

    reaction = Reaction.create(
        comment_id=uuid4(),
        author_id=uuid4(),
        author_role=UserRole.SUPPORT_AGENT,
        reaction_type=ReactionType(reaction_type),
    )

    assert reaction.reaction_type == reaction_type


@pytest.mark.parametrize("author_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
def test_customers_cannot_create_in_progress_reaction(author_role):
    """
    Клиенты не могут ставить реакции 'in_progress'
    """

    with pytest.raises(PermissionDeniedError, match="Customers cannot set 'In Progress' reaction"):
        Reaction.create(
            comment_id=uuid4(),
            author_id=uuid4(),
            author_role=author_role,
            reaction_type=ReactionType.IN_PROGRESS,
        )


def test_toggle_new_type_success(sample_reaction):
    """
    Успешное переключение реакции
    """

    sample_reaction.toggle(
        new_type=ReactionType.IN_PROGRESS,
        author_id=sample_reaction.author_id,
        author_role=UserRole.SUPPORT_MANAGER,
    )

    assert sample_reaction.reaction_type == ReactionType.IN_PROGRESS
    assert sample_reaction.updated_at != sample_reaction.created_at


def test_non_author_cannot_toggle_reaction(sample_reaction):
    """
    Только автор может переключать свои реакции
    """

    with pytest.raises(PermissionDeniedError, match="Only author can toggle his reaction"):
        sample_reaction.toggle(
            new_type=ReactionType.IMPORTANT,
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_AGENT,
        )


def test_customers_cannot_toggle_to_in_progress_reaction(sample_reaction):
    """
    Клиента не могут переключать на 'in_progress' реакцию
    """

    with pytest.raises(PermissionDeniedError, match="Customers cannot set 'In Progress' reaction"):
        sample_reaction.toggle(
            new_type=ReactionType.IN_PROGRESS,
            author_id=sample_reaction.author_id,
            author_role=UserRole.CUSTOMER,
        )


def test_toggle_to_same_reaction_do_nothing(sample_reaction):
    """
    При переключении на такую же реакцию - сущность не изменяется
    """

    sample_reaction.toggle(
        new_type=ReactionType.LIKE,
        author_id=sample_reaction.author_id,
        author_role=UserRole.SUPPORT_AGENT,
    )
    old_updated_at = sample_reaction.updated_at

    assert sample_reaction.reaction_type == ReactionType.LIKE
    assert sample_reaction.updated_at == old_updated_at
