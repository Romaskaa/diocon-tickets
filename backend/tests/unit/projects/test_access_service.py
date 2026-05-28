from uuid import UUID, uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.projects.domain.entities import Membership, Project
from src.projects.domain.services import (
    ProjectAccessService,
    generate_project_key,
    get_allowed_project_roles_for_user,
)
from src.projects.domain.vo import ProjectRole
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import TicketNumber, TicketStatus
from src.shared.utils.time import current_datetime

# Правильный набор ролей для добавления участника в проект
VALID_ROLES_SET = [
    # Клиенты
    (UserRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER),
    (UserRole.CUSTOMER, ProjectRole.CUSTOMER),
    (UserRole.CUSTOMER_ADMIN, ProjectRole.CUSTOMER_MANAGER),
    (UserRole.CUSTOMER_ADMIN, ProjectRole.CUSTOMER),
    (UserRole.CUSTOMER, ProjectRole.VIEWER),
    (UserRole.CUSTOMER_ADMIN, ProjectRole.VIEWER),
    # Менеджер поддержки
    (UserRole.SUPPORT_MANAGER, ProjectRole.MANAGER),
    (UserRole.SUPPORT_MANAGER, ProjectRole.CONTRIBUTOR),
    (UserRole.SUPPORT_MANAGER, ProjectRole.VIEWER),
    # Агент поддержки
    (UserRole.SUPPORT_AGENT, ProjectRole.MANAGER),
    (UserRole.SUPPORT_AGENT, ProjectRole.CONTRIBUTOR),
    (UserRole.SUPPORT_AGENT, ProjectRole.VIEWER),
]


@pytest.fixture
def access_service(fake_membership_repo):
    return ProjectAccessService(fake_membership_repo)


@pytest.fixture
def created_by():
    return uuid4()


@pytest.fixture
def counterparty_id():
    return uuid4()


@pytest.fixture
def active_project(created_by, counterparty_id):
    return Project.create(
        name="Тестовый проект",
        key="TEST",
        created_by=created_by,
        description="Проект для тестов",
        counterparty_id=counterparty_id,
    )


def make_membership(
        project_id: UUID, user_id: UUID, project_role: ProjectRole, is_deleted: bool = False
):
    return Membership(
        project_id=project_id,
        user_id=user_id,
        project_role=project_role,
        added_by=uuid4(),
        deleted_at=current_datetime() if is_deleted else None,
    )


def make_ticket(
        *,
        status: TicketStatus = TicketStatus.OPEN,
        counterparty_id: UUID | None = None,
) -> Ticket:
    ticket = Ticket.create(
        ticket_number=TicketNumber("INT-26-00000001"),
        reporter_id=uuid4(),
        created_by=uuid4(),
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Project access ticket",
        project_id=uuid4(),
        counterparty_id=counterparty_id,
    )
    ticket.status = status
    list(ticket.collect_events())
    return ticket


class TestGenerateProjectKey:
    """
    Проверяем генерацию ключа проекта: она нужна для endpoint key-suggestion
    и автоподстановки короткого идентификатора проекта.
    """

    def test_empty_name_returns_default_key(self):
        """
        Проверяем fallback генерации ключа: если имя пустое, сервис должен
        вернуть дефолтное значение, а не пустую строку.
        Данные: пустое имя проекта.
        """

        assert generate_project_key("") == "PRJ"

    def test_name_without_letters_returns_default_key(self):
        """
        Проверяем очистку имени проекта: если после удаления цифр и символов
        не осталось слов, сервис должен вернуть дефолтный ключ.
        Данные: строка только из цифр и знаков.
        """

        assert generate_project_key("123 !!!") == "PRJ"

    def test_single_short_word_is_extended_to_minimum_length(self):
        """
        Проверяем минимальную длину ключа: однобуквенное имя должно стать
        ключом из двух символов, чтобы пройти правила ProjectKey.
        Данные: название проекта из одной буквы.
        """

        assert generate_project_key("A") == "AA"

    def test_three_words_use_first_letters(self):
        """
        Проверяем генерацию по нескольким словам: для длинного названия берутся
        первые буквы первых трёх слов.
        Данные: название из трёх английских слов.
        """

        assert generate_project_key("Customer Support Portal") == "CSP"


class TestAllowedProjectRolesForUser:
    """
    Проверяем соответствие системной роли пользователя и разрешённых ролей
    внутри проекта. Это базовое правило используется при добавлении участников.
    """

    @pytest.mark.parametrize("user_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
    def test_customer_roles_get_customer_project_roles(self, user_role):
        """
        Проверяем клиентские системные роли: им нельзя назначать внутренние
        project-роли вроде MANAGER или CONTRIBUTOR.
        Данные: customer/customer_admin роль.
        """

        roles = get_allowed_project_roles_for_user(user_role)

        assert roles == {
            ProjectRole.VIEWER,
            ProjectRole.CUSTOMER,
            ProjectRole.CUSTOMER_MANAGER,
        }

    @pytest.mark.parametrize("user_role", [UserRole.SUPPORT_AGENT, UserRole.DEVELOPER])
    def test_internal_roles_get_internal_project_roles(self, user_role):
        """
        Проверяем внутренние системные роли: им нельзя назначать клиентские
        project-роли CUSTOMER и CUSTOMER_MANAGER.
        Данные: support/developer роль.
        """

        roles = get_allowed_project_roles_for_user(user_role)

        assert roles == {
            ProjectRole.VIEWER,
            ProjectRole.CONTRIBUTOR,
            ProjectRole.MANAGER,
        }


class TestCanCreateProject:
    """
    Тестовые сценарии для проверки прав на создание проекта
    """

    @pytest.mark.parametrize("user_role", [UserRole.SUPPORT_MANAGER, UserRole.ADMIN])
    def test_admin_or_support_manager_can_create_without_counterparty(
            self, access_service, user_role
    ):
        permission = access_service.can_create_project(user_role)

        assert permission.allowed is True

    def test_account_manager_with_counterparty_can_create(self, access_service):
        permission = access_service.can_create_project(UserRole.ACCOUNT_MANAGER, uuid4())

        assert permission.allowed is True

    def test_account_manager_cannot_create_without_counterparty(self, access_service):
        permission = access_service.can_create_project(UserRole.ACCOUNT_MANAGER)

        assert permission.allowed is False
        assert "counterparty" in permission.reason.lower()

    @pytest.mark.parametrize(
        "user_role", [
            UserRole.CUSTOMER,
            UserRole.CUSTOMER_ADMIN,
            UserRole.SUPPORT_AGENT,
            UserRole.FINANCE,
            UserRole.DEVELOPER,
        ]
    )
    def test_other_roles_cannot_create(self, access_service, user_role):
        permission = access_service.can_create_project(user_role)

        assert permission.allowed is False


class TestCanAddMembers:
    """
    Тестовые сценарии для проверки прав на добавление участников в проект
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target_user_role", list(UserRole))
    async def test_owner_role_cannot_be_assigned(
            self, access_service, active_project, target_user_role
    ):
        """
        Нельзя назначить роль владельца проекта через добавление участника
        """

        permission = await access_service.can_add_members(
            project=active_project,
            target_user_role=target_user_role,
            target_project_role=ProjectRole.OWNER,
            user_id=uuid4(),
            user_role=UserRole.ADMIN,
        )

        assert permission.allowed is False
        assert "OWNER role cannot be assigned" in permission.reason

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target_user_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
    async def test_customer_cannot_get_internal_role(
            self, access_service, active_project, target_user_role
    ):
        """
        Клиенту нельзя назначить внутреннею роль в проекте
        """

        for project_role in {ProjectRole.MANAGER, ProjectRole.CONTRIBUTOR}:
            permission = await access_service.can_add_members(
                project=active_project,
                target_user_role=target_user_role,
                target_project_role=project_role,
                user_id=uuid4(),
                user_role=UserRole.SUPPORT_AGENT,
            )

            assert permission.allowed is False
            assert "cannot be assigned project role" in permission.reason

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_user_role", [user_role for user_role in UserRole if user_role.is_internal()]
    )
    async def test_internal_user_cannot_get_customer_role(
            self, access_service, active_project, target_user_role
    ):
        """
        Внутреннему сотруднику нельзя назначить клиентскую роль в проекте
        """

        for project_role in {ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER}:
            permission = await access_service.can_add_members(
                project=active_project,
                target_user_role=target_user_role,
                target_project_role=project_role,
                user_id=uuid4(),
                user_role=UserRole.SUPPORT_AGENT,
            )

            assert permission.allowed is False
            assert "cannot be assigned project role" in permission.reason

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("target_user_role", "target_project_role"), VALID_ROLES_SET)
    async def test_creator_or_owner_can_add_any_valid_member(
            self, access_service, active_project, target_user_role, target_project_role
    ):
        """
        Создатель или владелец проекта может добавлять участников с правильной ролью
        """

        for user_id in {active_project.created_by, active_project.owner_id}:
            permission = await access_service.can_add_members(
                project=active_project,
                target_user_role=target_user_role,
                target_project_role=target_project_role,
                user_id=user_id,
                user_role=UserRole.SUPPORT_MANAGER,
            )

            assert permission.allowed is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("target_user_role", "target_project_role"), VALID_ROLES_SET)
    async def test_admin_can_add_any_valid_member(
            self, access_service, active_project, target_user_role, target_project_role
    ):
        """
        Администратор может добавлять любых участников с валидной ролью
        """

        permission = await access_service.can_add_members(
            project=active_project,
            target_user_role=target_user_role,
            target_project_role=target_project_role,
            user_id=uuid4(),
            user_role=UserRole.ADMIN,
        )

        assert permission.allowed is True

    @pytest.mark.asyncio
    async def test_non_member_cannot_add_member(self, access_service, active_project):
        """
        Не участник проекта не может добавлять новых участников в проект
        """

        permission = await access_service.can_add_members(
            project=active_project,
            target_user_role=UserRole.CUSTOMER,
            target_project_role=ProjectRole.CUSTOMER,
            user_id=uuid4(),
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert permission.allowed is False
        assert "your are not member of the project" in permission.reason.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("target_user_role", "target_project_role"), VALID_ROLES_SET)
    async def test_project_manager_can_add_any_valid_member(
            self,
            access_service,
            active_project,
            fake_membership_repo,
            target_user_role,
            target_project_role,
    ):
        """
        Менеджер проекта может добавлять любых участников
        """

        user_id = uuid4()
        membership = make_membership(
            project_id=active_project.id,
            user_id=user_id,
            project_role=ProjectRole.MANAGER,
        )
        await fake_membership_repo.create(membership)

        permission = await access_service.can_add_members(
            project=active_project,
            target_user_role=target_user_role,
            target_project_role=target_project_role,
            user_id=user_id,
            user_role=UserRole.SUPPORT_MANAGER,
        )

        assert permission.allowed is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("target_user_role", "target_project_roles"),
        [
            (UserRole.CUSTOMER, {ProjectRole.VIEWER, ProjectRole.CUSTOMER}),
            (UserRole.CUSTOMER_ADMIN, {ProjectRole.VIEWER, ProjectRole.CUSTOMER}),
            (UserRole.SUPPORT_AGENT, {ProjectRole.VIEWER, ProjectRole.CONTRIBUTOR}),
            (UserRole.DEVELOPER, {ProjectRole.VIEWER, ProjectRole.CONTRIBUTOR}),
            (UserRole.SUPPORT_MANAGER, {ProjectRole.VIEWER, ProjectRole.CONTRIBUTOR}),
        ]
    )
    async def test_contributor_can_add_limited_roles(
            self,
            access_service,
            active_project,
            fake_membership_repo,
            target_user_role,
            target_project_roles
    ):
        """
        CONTRIBUTOR проекта может добавлять участников с ограниченным набором ролей
        """

        user_id = uuid4()
        contributor = make_membership(
            project_id=active_project.id,
            user_id=user_id,
            project_role=ProjectRole.CONTRIBUTOR,
        )
        await fake_membership_repo.create(contributor)

        for target_project_role in target_project_roles:
            permission = await access_service.can_add_members(
                project=active_project,
                target_user_role=target_user_role,
                target_project_role=target_project_role,
                user_id=user_id,
                user_role=UserRole.SUPPORT_AGENT,
            )

            assert permission.allowed is True

    @pytest.mark.asyncio
    async def test_contributor_cannot_add_manager(
            self, access_service, active_project, fake_membership_repo
    ):
        """
        CONTRIBUTOR не может добавить менеджера проекта
        """

        user_id = uuid4()
        contributor = make_membership(
            project_id=active_project.id,
            user_id=user_id,
            project_role=ProjectRole.CONTRIBUTOR,
        )
        await fake_membership_repo.create(contributor)

        permission = await access_service.can_add_members(
            project=active_project,
            target_user_role=UserRole.SUPPORT_MANAGER,
            target_project_role=ProjectRole.MANAGER,
            user_id=user_id,
            user_role=UserRole.DEVELOPER,
        )

        assert permission.allowed is False
        assert "contributor can add only members with roles" in permission.reason.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_project_role", [ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER]
    )
    async def test_customer_manager_can_add_customers(
            self, access_service, active_project, fake_membership_repo, target_project_role
    ):
        """
        Менеджер клиентов может добавлять только клиентов в проект
        """

        user_id = uuid4()
        customer_manager = make_membership(
            project_id=active_project.id,
            user_id=user_id,
            project_role=ProjectRole.CUSTOMER_MANAGER,
        )
        await fake_membership_repo.create(customer_manager)

        permission = await access_service.can_add_members(
            project=active_project,
            target_user_role=UserRole.CUSTOMER,
            target_project_role=target_project_role,
            user_id=user_id,
            user_role=UserRole.CUSTOMER_ADMIN,
        )

        assert permission.allowed is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_project_role", [ProjectRole.CONTRIBUTOR, ProjectRole.MANAGER]
    )
    async def test_customer_manager_cannot_add_internal_roles(
            self, access_service, active_project, fake_membership_repo, target_project_role
    ):
        """
        Менеджер клиентов не может добавлять участников с внутренними проектными ролями
        """

        user_id = uuid4()
        customer_manager = make_membership(
            project_id=active_project.id,
            user_id=user_id,
            project_role=ProjectRole.CUSTOMER_MANAGER,
        )
        await fake_membership_repo.create(customer_manager)

        permission = await access_service.can_add_members(
            project=active_project,
            target_user_role=UserRole.SUPPORT_AGENT,
            target_project_role=target_project_role,
            user_id=user_id,
            user_role=UserRole.CUSTOMER,
        )

        assert permission.allowed is False
        assert "customer manager can add only members with roles" in permission.reason.lower()

    @pytest.mark.asyncio
    async def test_deleted_member_cannot_add(
            self, access_service, active_project, fake_membership_repo
    ):
        """
        Удалённый участник не может добавлять новых участников
        """

        user_id = uuid4()
        membership = make_membership(
            project_id=active_project.id,
            user_id=user_id,
            project_role=ProjectRole.CONTRIBUTOR,
            is_deleted=True
        )
        await fake_membership_repo.create(membership)

        permission = await access_service.can_add_members(
            project=active_project,
            target_user_role=UserRole.SUPPORT_AGENT,
            target_project_role=ProjectRole.CONTRIBUTOR,
            user_id=user_id,
            user_role=UserRole.DEVELOPER,
        )

        assert permission.allowed is False


class TestCanArchiveProject:
    """
    Тест-кейсы архивации проекта
    """

    def test_admin_can_archive(self, access_service, active_project):
        """
        Системный администратор может архивировать любой проект
        """

        permission = access_service.can_archive_project(
            project=active_project, user_id=uuid4(), user_role=UserRole.ADMIN
        )

        assert permission.allowed is True

    def test_creator_or_owner_can_archive(self, access_service, active_project):
        """
        Создатель или владелец могут архивировать проект
        """

        for user_id in [active_project.created_by, active_project.owner_id]:
            permission = access_service.can_archive_project(
                project=active_project, user_id=user_id, user_role=UserRole.SUPPORT_AGENT,
            )
            assert permission.allowed is True

    @pytest.mark.parametrize(
        "user_role", [
            UserRole.SUPPORT_MANAGER,
            UserRole.SUPPORT_AGENT,
            UserRole.DEVELOPER,
            UserRole.ACCOUNT_MANAGER,
            UserRole.FINANCE,
            UserRole.CUSTOMER,
            UserRole.CUSTOMER_ADMIN,
        ]
    )
    def test_other_user_cannot_archive(self, access_service, active_project, user_role):
        """
        Только админ, фактический создатель и владелец могут архивировать проект
        """

        permission = access_service.can_archive_project(
            project=active_project, user_id=uuid4(), user_role=user_role
        )
        assert permission.allowed is False
