from uuid import UUID, uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.projects.domain.entities import Membership, Project
from src.projects.domain.services import ProjectAccessService
from src.projects.domain.vo import ProjectRole
from src.shared.utils.time import current_datetime


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
    async def test_owner_role_cannot_be_assigned(self, access_service, active_project):
        """
        Нельзя назначить роль владельца проекта путём добавления участника
        """

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=ProjectRole.OWNER,
            user_id=uuid4(),
            user_role=UserRole.ADMIN,
        )

        assert permission.allowed is False
        assert "OWNER role cannot be assigned" in permission.reason

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_role", [
            ProjectRole.CUSTOMER_MANAGER,
            ProjectRole.CUSTOMER,
            ProjectRole.VIEWER,
            ProjectRole.CONTRIBUTOR,
            ProjectRole.MANAGER,
        ]
    )
    async def test_project_creator_can_add_any_roles_except_owner(
            self, access_service, active_project, created_by, target_role
    ):
        """
        Создатель/владелец проекта может добавлять участников с любой ролью
        кроме владельца
        """

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=target_role,
            user_id=created_by,
            user_role=UserRole.SUPPORT_MANAGER,
        )

        assert permission.allowed is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_role",
        [
            ProjectRole.CUSTOMER_MANAGER,
            ProjectRole.CUSTOMER,
            ProjectRole.VIEWER,
            ProjectRole.CONTRIBUTOR,
            ProjectRole.MANAGER,
        ],
    )
    async def test_admin_can_add_any_role(self, access_service, active_project, target_role):
        """
        Системный администратор может добавлять участников в любой проект
        """

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=target_role,
            user_id=uuid4(),
            user_role=UserRole.ADMIN
        )

        assert permission.allowed is True

    @pytest.mark.asyncio
    async def test_non_member_is_denied(self, access_service, active_project):
        """
        Чтобы добавлять других участников, нужно самому состоять в проекте
        """

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=ProjectRole.VIEWER,
            user_id=uuid4(),
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert permission.allowed is False
        assert "not member" in permission.reason.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_role",
        [
            ProjectRole.CUSTOMER_MANAGER,
            ProjectRole.CUSTOMER,
            ProjectRole.VIEWER,
            ProjectRole.CONTRIBUTOR,
            ProjectRole.MANAGER,
        ],
    )
    async def test_manager_can_add_any_role(
            self, access_service, active_project, fake_membership_repo, target_role
    ):
        """
        Менеджер проекта может добавлять участника с любой ролью кроме владельца
        """

        # Создание менеджера проекта
        user_id = uuid4()
        manager = make_membership(
            project_id=active_project.id, user_id=user_id, project_role=ProjectRole.MANAGER
        )
        await fake_membership_repo.create(manager)

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=target_role,
            user_id=user_id,
            user_role=UserRole.SUPPORT_AGENT,
        )

        assert permission.allowed is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_role", [
            ProjectRole.VIEWER,
            ProjectRole.CONTRIBUTOR,
            ProjectRole.CUSTOMER,
        ]
    )
    async def test_contributor_can_add_limited_set_of_roles(
            self, access_service, active_project, fake_membership_repo, target_role
    ):
        """
        CONTRIBUTOR может добавлять только: VIEWER, CUSTOMER, CONTRIBUTOR
        """

        # Создание участника с ролью CONTRIBUTOR
        user_id = uuid4()
        contributor = make_membership(
            project_id=active_project.id, project_role=ProjectRole.CONTRIBUTOR, user_id=user_id
        )
        await fake_membership_repo.create(contributor)

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=target_role,
            user_id=user_id,
            user_role=UserRole.SUPPORT_MANAGER,
        )

        assert permission.allowed is True

    @pytest.mark.asyncio
    async def test_contributor_cannot_add_project_manager(
            self, access_service, active_project, fake_membership_repo
    ):
        """
        CONTRIBUTOR не может добавить менеджера проекта
        """

        # Создание участника с ролью CONTRIBUTOR
        user_id = uuid4()
        contributor = make_membership(
            project_id=active_project.id, project_role=ProjectRole.CONTRIBUTOR, user_id=user_id
        )
        await fake_membership_repo.create(contributor)

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=ProjectRole.MANAGER,
            user_id=user_id,
            user_role=UserRole.DEVELOPER,
        )

        assert permission.allowed is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target_role", [ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_MANAGER])
    async def test_customer_manager_can_add_customer_roles(
            self, access_service, active_project, fake_membership_repo, target_role
    ):
        """
        Клиент внутри проекта может добавлять участников с клиентскими ролями
        """

        # Создание участника с ролью CUSTOMER_MANAGER
        user_id = uuid4()
        customer_manager = make_membership(
            project_id=active_project.id,
            project_role=ProjectRole.CUSTOMER_MANAGER,
            user_id=user_id,
        )
        await fake_membership_repo.create(customer_manager)

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=target_role,
            user_id=user_id,
            user_role=UserRole.CUSTOMER_ADMIN,
        )

        assert permission.allowed is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target_role", [ProjectRole.CONTRIBUTOR, ProjectRole.MANAGER])
    async def test_customer_manager_cannot_add_staff_members(
            self, access_service, active_project, fake_membership_repo, target_role
    ):
        """
        Клиент не может добавлять внутренних сотрудников
        """

        # Создание участника с ролью CUSTOMER_MANAGER
        user_id = uuid4()
        customer_manager = make_membership(
            project_id=active_project.id,
            project_role=ProjectRole.CUSTOMER_MANAGER,
            user_id=user_id,
        )
        await fake_membership_repo.create(customer_manager)

        permission = await access_service.can_add_members(
            project=active_project,
            target_role=target_role,
            user_id=user_id,
            user_role=UserRole.CUSTOMER_ADMIN,
        )

        assert permission.allowed is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target_role", list(ProjectRole))
    async def test_customer_or_viewer_cannot_add_members(
            self, access_service, active_project, fake_membership_repo, target_role
    ):
        """
        Наблюдатель или клиент не могут добавлять никаких участников
        """

        customer = make_membership(
            project_id=active_project.id,
            project_role=ProjectRole.CUSTOMER,
            user_id=uuid4(),
        )
        viewer = make_membership(
            project_id=active_project.id,
            project_role=ProjectRole.VIEWER,
            user_id=uuid4(),
        )

        for membership in [customer, viewer]:
            await fake_membership_repo.create(customer)

            permission = await access_service.can_add_members(
                project=active_project,
                target_role=target_role,
                user_id=membership.user_id,
                user_role=UserRole.CUSTOMER_ADMIN,
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
