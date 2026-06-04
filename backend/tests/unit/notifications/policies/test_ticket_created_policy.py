import random
from uuid import UUID, uuid4

import pytest
from faker import Faker
from pydantic import SecretStr

from src.iam.domain.entities import User
from src.iam.domain.vo import FullName, Username, UserRole
from src.notifications.policies import TicketCreatedPolicy
from src.tickets.domain.entities import Membership, Project
from src.tickets.domain.events import TicketCreated
from src.tickets.domain.vo import ProjectKey, ProjectRole, ProjectStatus, TicketPriority

fake = Faker("ru_RU")


@pytest.fixture
def policy(mock_project_repo, mock_user_repo):
    return TicketCreatedPolicy(project_repo=mock_project_repo, user_repo=mock_user_repo)


@pytest.fixture
def sample_ticket_created_event():
    return TicketCreated(
        ticket_id=uuid4(),
        number="ROM-26-00000123",
        title="Не работает оплата",
        reporter_id=uuid4(),
        created_by=uuid4(),
        priority=TicketPriority.HIGH,
        counterparty_id=None,
        project_id=None,
    )


# ====================== Вспомогательные фабрики ======================

def fake_user(**kwargs):
    return User(
        id=uuid4(),
        email=fake.email(),
        username=Username(fake.user_name()),
        full_name=FullName("Иванов Иван Иванович"),
        role=kwargs.get("role", UserRole.SUPPORT_AGENT),
        counterparty_id=kwargs.get("counterparty_id"),
        password_hash=SecretStr("hashed"),
        is_active=True,
    )


def fake_membership(user_id: UUID, project_role: ProjectRole):
    return Membership(
        project_id=uuid4(),
        user_id=user_id,
        project_role=project_role,
        added_by=uuid4(),
    )


def fake_project(project_id: UUID, memberships: list[Membership]):
    owner_id = uuid4()
    return Project(
        id=project_id,
        name=fake.company(),
        key=ProjectKey("TEST"),
        status=ProjectStatus.ACTIVE,
        owner_id=owner_id,
        memberships=[
            fake_membership(user_id=owner_id, project_role=ProjectRole.OWNER), *memberships
        ],
        created_by=uuid4(),
    )


# ====================== Тесты ======================

class TestTicketCreatedPolicy:
    """
    Тестирование политики уведомлений для события созданного тикета
    """

    @pytest.mark.asyncio
    async def test_reporter_always_receives_notification(
            self, policy, sample_ticket_created_event
    ):
        """
        Инициатор тикета должен всегда получать уведомление
        """

        targets = await policy.get_targets(sample_ticket_created_event)
        assert sample_ticket_created_event.reporter_id in targets

    @pytest.mark.asyncio
    async def test_customer_admin_receives_notification(
            self, policy, sample_ticket_created_event, mock_user_repo
    ):
        """
        Администратор контрагента всегда должен получать уведомление
        """

        counterparty_id = uuid4()
        customer_admin = fake_user(role=UserRole.CUSTOMER_ADMIN, counterparty_id=counterparty_id)

        await mock_user_repo.create(customer_admin)

        event = TicketCreated(
            ticket_id=sample_ticket_created_event.ticket_id,
            number=sample_ticket_created_event.number,
            title=sample_ticket_created_event.title,
            reporter_id=sample_ticket_created_event.reporter_id,
            created_by=sample_ticket_created_event.created_by,
            priority=sample_ticket_created_event.priority,
            counterparty_id=counterparty_id,
        )

        targets = await policy.get_targets(event)

        assert customer_admin.id in targets
        assert sample_ticket_created_event.reporter_id in targets

    @pytest.mark.asyncio
    async def test_project_support_members_receive_notification(
            self, sample_ticket_created_event, policy, mock_project_repo
    ):
        """
        Участники проекта с поддерживаемыми ролями должны получать уведомление
        """

        project_id = uuid4()
        customer_id = uuid4()
        project_member_id = uuid4()
        support_member = fake_user(role=UserRole.SUPPORT_AGENT)

        project = fake_project(
            project_id=project_id,
            memberships=[
                fake_membership(user_id=support_member.id, project_role=ProjectRole.MANAGER),
                fake_membership(user_id=project_member_id, project_role=ProjectRole.MEMBER),
                fake_membership(user_id=customer_id, project_role=ProjectRole.CUSTOMER),
            ]
        )
        await mock_project_repo.create(project)

        event = TicketCreated(
            ticket_id=sample_ticket_created_event.ticket_id,
            number=sample_ticket_created_event.number,
            title=sample_ticket_created_event.title,
            reporter_id=sample_ticket_created_event.reporter_id,
            created_by=sample_ticket_created_event.created_by,
            priority=sample_ticket_created_event.priority,
            project_id=project_id,
        )

        targets = await policy.get_targets(event)

        assert support_member.id in targets
        assert customer_id not in targets
        assert project_member_id in targets

    @pytest.mark.asyncio
    async def test_fallback_to_all_supports(
            self, policy, sample_ticket_created_event, mock_user_repo
    ):
        """
        Если не указан проект, то уведомить всех сотрудников поддержки
        """

        supports = [
            fake_user(role=random.choice([UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]))  # noqa: S311
            for _ in range(50)
        ]
        for support in supports:
            await mock_user_repo.create(support)

        targets = await policy.get_targets(sample_ticket_created_event)

        supports_ids = [support.id for support in supports]

        assert len(set(supports_ids)) == len(supports)
        assert set(supports_ids).issubset(set(targets))

    @pytest.mark.asyncio
    async def test_all_required_users_receive_notification(
            self, policy, sample_ticket_created_event, mock_user_repo
    ):
        """
        Все необходимые пользователи должны получить уведомление (проект не указан)
        """

        counterparty_id = uuid4()
        customer_admin = fake_user(role=UserRole.CUSTOMER_ADMIN, counterparty_id=counterparty_id)
        await mock_user_repo.create(customer_admin)

        supports = [
            fake_user(role=random.choice([UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]))  # noqa: S311
            for _ in range(50)
        ]
        for support in supports:
            await mock_user_repo.create(support)

        event = TicketCreated(
            ticket_id=sample_ticket_created_event.ticket_id,
            number=sample_ticket_created_event.number,
            title=sample_ticket_created_event.title,
            reporter_id=sample_ticket_created_event.reporter_id,
            created_by=sample_ticket_created_event.created_by,
            priority=sample_ticket_created_event.priority,
            counterparty_id=counterparty_id,
        )

        targets = await policy.get_targets(event)

        supports_ids = [support.id for support in supports]

        all_ids = [*supports_ids, customer_admin.id, event.reporter_id]

        assert len(all_ids) == len(targets)
        assert set(all_ids).issubset(set(targets))

    @pytest.mark.asyncio
    async def test_all_required_memberships_receive_notification(
            self, policy, sample_ticket_created_event, mock_user_repo, mock_project_repo
    ):
        """
        Все необходимые участники проекта получат уведомление
        """

        project_id = uuid4()
        customer_id = uuid4()
        counterparty_id = uuid4()
        project_member_id = uuid4()
        support_member = fake_user(role=UserRole.SUPPORT_AGENT)

        customer_admin = fake_user(role=UserRole.CUSTOMER_ADMIN, counterparty_id=counterparty_id)
        await mock_user_repo.create(customer_admin)

        project = fake_project(
            project_id=project_id,
            memberships=[
                fake_membership(user_id=support_member.id, project_role=ProjectRole.MANAGER),
                fake_membership(user_id=project_member_id, project_role=ProjectRole.MEMBER),
                fake_membership(user_id=customer_id, project_role=ProjectRole.CUSTOMER),
            ],
        )
        await mock_project_repo.create(project)

        supports = [
            fake_user(role=random.choice([UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER]))  # noqa: S311
            for _ in range(50)
        ]
        for support in supports:
            await mock_user_repo.create(support)

        event = TicketCreated(
            ticket_id=sample_ticket_created_event.ticket_id,
            number=sample_ticket_created_event.number,
            title=sample_ticket_created_event.title,
            reporter_id=sample_ticket_created_event.reporter_id,
            created_by=sample_ticket_created_event.created_by,
            priority=sample_ticket_created_event.priority,
            project_id=project_id,
            counterparty_id=counterparty_id,
        )

        targets = await policy.get_targets(event)

        all_ids = [
            support_member.id,
            project_member_id,
            customer_admin.id,
            event.reporter_id,
            project.owner_id,
        ]

        assert len(all_ids) == len(targets)
        assert set(all_ids) == set(targets)
