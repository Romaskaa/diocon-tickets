from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.crm.domain.entities import Counterparty
from src.crm.domain.repo import CounterpartyRepository
from src.crm.domain.vo import CounterpartyType, Inn, Kpp, Phone
from src.iam.domain.entities import User
from src.iam.domain.repos import InvitationRepository, TokenBlacklist, UserRepository
from src.iam.domain.vo import FullName, UserRole
from src.notifications.domain.repos import NotificationRepository, PreferenceRepository
from src.products.domain.repo import ProductRepository
from src.projects.domain.entities import Membership, Project
from src.projects.domain.repos import MembershipRepository, ProjectRepository
from src.projects.domain.services import ProjectAccessService
from src.projects.domain.vo import ProjectRole
from src.shared.domain.events import EventPublisher
from src.shared.infra.events import EventBus
from src.shared.utils.time import current_datetime
from src.tasks.domain.repos import TaskRepository
from src.tickets.domain.entities import Ticket
from src.tickets.domain.repos import (
    CommentRepository,
    ReactionRepository,
    TicketRepository,
)
from src.tickets.domain.vo import Priority, Tag, TicketNumber, TicketStatus, TicketType

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
    InMemoryTaskRepository,
    InMemoryTicketRepository,
    InMemoryTokenBlacklist,
    InMemoryUserRepository,
)

# ============================= In memory репозитории =============================


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
def fake_task_repo() -> TaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def event_publisher() -> EventPublisher:
    return EventBus(max_queue_size=10)


@pytest.fixture
def fake_project_access_service(fake_membership_repo) -> ProjectAccessService:
    return ProjectAccessService(fake_membership_repo)


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


# ============================= Фабрики для создания сущностей =============================


@pytest.fixture
def counterparty_factory(fake_counterparty_repo):

    async def _make_counterparty(**overrides):
        counterparty_type = overrides.pop("counterparty_type", CounterpartyType.LEGAL_ENTITY)
        inn = overrides.pop("inn", None)
        kpp = overrides.pop("kpp", None)

        if inn is None:
            if counterparty_type in {
                CounterpartyType.INDIVIDUAL, CounterpartyType.INDIVIDUAL_ENTREPRENEUR
            }:
                inn = Inn("123456789012")
            else:
                inn = Inn("1234567890")

        if counterparty_type in {CounterpartyType.LEGAL_ENTITY, CounterpartyType.BRANCH} \
                and kpp is None:
            kpp = Kpp("123456789")
        else:
            kpp = None

        counterparty = Counterparty(
            id=overrides.pop("id", uuid4()),
            counterparty_type=counterparty_type,
            name=overrides.pop("name", "Тестовый контрагент"),
            legal_name=overrides.pop("legal_name", "ООО «Тест»"),
            inn=inn,
            kpp=kpp,
            email=overrides.pop("email", "test.counterparty@test.com"),
            phone=overrides.pop("phone", Phone("88005553535")),
            parent_id=overrides.pop("parent_id", None),
        )
        await fake_counterparty_repo.create(counterparty)
        return counterparty

    return _make_counterparty


@pytest.fixture
def user_factory(fake_user_repo):

    async def _make_user(role: UserRole, **overrides):
        user_id = overrides.pop("id", uuid4())
        email = overrides.pop("email", f"user.{role}@test.com")
        full_name = overrides.pop("full_name", "Тестов Тест Тестович")
        password_hash = SecretStr("123456789")
        counterparty_id = None

        if role.is_customer():
            counterparty_id = overrides.pop("counterparty_id", uuid4())

        user = User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            role=role,
            counterparty_id=counterparty_id,
            full_name=FullName(full_name),
        )
        await fake_user_repo.create(user)
        return user

    return _make_user


@pytest.fixture
def project_factory(fake_project_repo):

    async def _make_project(**overrides):
        project = Project.create(
            name=overrides.pop("name", "Test Project"),
            key=overrides.pop("key", "TESTPRJ"),
            created_by=overrides.pop("created_by", uuid4()),
            counterparty_id=overrides.pop("counterparty_id", None)
        )
        await fake_project_repo.create(project)
        return project

    return _make_project


@pytest.fixture
def membership_factory(fake_membership_repo):

    async def _make_membership(
            user_id: UUID, project_id: UUID, project_role: ProjectRole, **overrides
    ):
        membership = Membership(
            user_id=user_id,
            project_id=project_id,
            project_role=project_role,
            added_by=overrides.pop("added_by", uuid4()),
            added_at=overrides.pop("added_at", current_datetime())
        )
        await fake_membership_repo.create(membership)
        return membership

    return _make_membership


@pytest.fixture
def ticket_factory(fake_ticket_repo):

    async def _make_ticket(status: TicketStatus = TicketStatus.NEW, **overrides):

        assignee_id = overrides.pop("assignee_id", None)
        if status in {TicketStatus.IN_PROGRESS, TicketStatus.CLOSED} and assignee_id is None:
            assignee_id = uuid4()

        closed_at = overrides.pop("closed_at", None)
        if status == TicketStatus.CLOSED and closed_at is None:
            closed_at = current_datetime()

        ticket = Ticket(
            id=overrides.pop("id", uuid4()),
            created_by=overrides.pop("created_by", uuid4()),
            created_by_role=overrides.pop("created_by_role", UserRole.SUPPORT_AGENT),
            reporter_id=overrides.pop("reporter_id", uuid4()),
            number=overrides.pop("number", TicketNumber("TEST-26-00000001")),
            title=overrides.pop("title", "Test title"),
            description=overrides.pop("description", "Test description"),
            type=overrides.pop("type", TicketType.SERVICE_REQUEST),
            status=status,
            priority=overrides.pop("priority", Priority.MEDIUM),
            assignee_id=assignee_id,
            closed_at=closed_at,
            project_id=overrides.pop("project_id", None),
            counterparty_id=overrides.pop("counterparty_id", None),
            product_id=overrides.pop("product_id", None),
            tags=overrides.pop("tags", []),
            attachments=overrides.pop("attachments", []),
            history=overrides.pop("history", []),
            created_at=overrides.pop("created_at", current_datetime()),
            updated_at=overrides.pop("updated_at", current_datetime()),
            deleted_at=overrides.pop("deleted_at", None),
        )
        await fake_ticket_repo.create(ticket)
        return ticket

    return _make_ticket
