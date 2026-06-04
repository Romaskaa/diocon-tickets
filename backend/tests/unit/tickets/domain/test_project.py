from uuid import UUID, uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvariantViolationError
from src.tickets.domain.entities import Project
from src.tickets.domain.vo import ProjectKey, ProjectRole, ProjectStatus


@pytest.fixture
def owner_id() -> UUID:
    return uuid4()


@pytest.fixture
def created_by() -> UUID:
    return uuid4()


@pytest.fixture
def manager_id() -> UUID:
    return uuid4()


@pytest.fixture
def member_id() -> UUID:
    return uuid4()


@pytest.fixture
def viewer_id() -> UUID:
    return uuid4()


@pytest.fixture
def counterparty_id() -> UUID:
    return uuid4()


@pytest.fixture
def project_data(owner_id, created_by, counterparty_id):
    return {
        "name": "Test Project",
        "key": "TEST",
        "owner_id": owner_id,
        "created_by": created_by,
        "description": "Test description",
        "counterparty_id": counterparty_id,
    }


@pytest.fixture
def created_project(project_data) -> Project:
    return Project.create(**project_data)


class TestProjectCreate:
    def test_create_should_succeed_with_valid_data(self, project_data):
        project = Project.create(**project_data)

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.key == ProjectKey("TEST")
        assert project.status == ProjectStatus.ACTIVE
        assert project.owner_id == project_data["owner_id"]
        assert len(project.memberships) == 1
        assert project.memberships[0].user_id == project_data["owner_id"]
        assert project.memberships[0].project_role == ProjectRole.OWNER
        assert project.memberships[0].added_by == project_data["created_by"]

    def test_create_should_raise_error_when_name_empty(self, owner_id, created_by):
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            Project.create(
                name="   ",
                key="TEST",
                owner_id=owner_id,
                created_by=created_by,
            )

    def test_create_should_raise_error_when_key_invalid(self, owner_id, created_by):
        with pytest.raises(ValueError, match="Invalid project key format"):
            Project.create(
                name="Test",
                key="1INVALID",
                owner_id=owner_id,
                created_by=created_by,
            )


class TestProjectParticipants:
    def test_add_participant_should_succeed_when_called_by_owner(
        self, created_project, manager_id, owner_id
    ):
        created_project.add_member(
            user_id=manager_id,
            project_role=ProjectRole.MANAGER,
            added_by=owner_id,
            added_by_role=UserRole.CUSTOMER_ADMIN,
        )
        excepted_memberships_count = 2

        assert len(created_project.memberships) == excepted_memberships_count
        added = next(
            participant for participant in created_project.memberships
            if participant.user_id == manager_id
        )
        assert added.project_role == ProjectRole.MANAGER
        assert added.added_by == owner_id

    def test_add_member_should_raise_error_when_user_already_member(
        self, created_project, owner_id
    ):
        with pytest.raises(InvariantViolationError, match="is already a member"):
            created_project.add_member(
                user_id=owner_id,
                project_role=ProjectRole.MEMBER,
                added_by=owner_id,
                added_by_role=UserRole.SUPPORT_AGENT,
            )

    def test_add_member_should_raise_permission_error_when_not_owner_or_manager(
        self, created_project, member_id, viewer_id
    ):
        created_project.add_member(
            user_id=member_id,
            project_role=ProjectRole.MEMBER,
            added_by=created_project.owner_id,
            added_by_role=UserRole.CUSTOMER_ADMIN,
        )
        with pytest.raises(
            PermissionDeniedError, match="Only owner or support stuff can add memberships"
        ):
            created_project.add_member(
                user_id=viewer_id,
                project_role=ProjectRole.VIEWER,
                added_by=member_id,
                added_by_role=UserRole.CUSTOMER,
            )
