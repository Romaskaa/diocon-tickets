from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.crm.domain.repo import CounterpartyRepository
from src.iam.domain.repos import InvitationRepository, TokenBlacklist, UserRepository
from src.notifications.domain.repos import NotificationRepository, PreferenceRepository
from src.products.domain.repo import ProductRepository
from src.projects.domain.repos import MembershipRepository, ProjectRepository
from src.shared.domain.events import EventPublisher
from src.shared.infra.events import EventBus
from src.tickets.domain.repos import (
    CommentRepository,
    ReactionRepository,
    TicketRepository,
)

from .in_memory_repos import (
    InMemoryCommentRepository,
    InMemoryCounterpartyRepository,
    InMemoryInvitationRepository,
    InMemoryMembershipRepository,
    InMemoryNotificationRepository,
    InMemoryPreferenceRepository,
    InMemoryProductRepository,
    InMemoryProjectRepository,
    InMemoryReactionRepository,
    InMemoryTicketRepository,
    InMemoryTokenBlacklist,
    InMemoryUserRepository,
)


@pytest.fixture
def fake_counterparty_repo() -> CounterpartyRepository:
    return InMemoryCounterpartyRepository()


@pytest.fixture
def fake_user_repo() -> UserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def fake_invitation_repo() -> InvitationRepository:
    return InMemoryInvitationRepository()


@pytest.fixture
def fake_token_blacklist() -> TokenBlacklist:
    return InMemoryTokenBlacklist()


@pytest.fixture
def fake_project_repo() -> ProjectRepository:
    return InMemoryProjectRepository()


@pytest.fixture
def fake_membership_repo() -> MembershipRepository:
    return InMemoryMembershipRepository()


@pytest.fixture
def fake_ticket_repo() -> TicketRepository:
    return InMemoryTicketRepository()


@pytest.fixture
def fake_comment_repo() -> CommentRepository:
    return InMemoryCommentRepository()


@pytest.fixture
def fake_preference_repo() -> PreferenceRepository:
    return InMemoryPreferenceRepository()


@pytest.fixture
def fake_notification_repo() -> NotificationRepository:
    return InMemoryNotificationRepository()


@pytest.fixture
def fake_reaction_repo() -> ReactionRepository:
    return InMemoryReactionRepository()


@pytest.fixture
def fake_product_repo() -> ProductRepository:
    return InMemoryProductRepository()


@pytest.fixture
def event_publisher() -> EventPublisher:
    return EventBus(max_queue_size=10)


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)
