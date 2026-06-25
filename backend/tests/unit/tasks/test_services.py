from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import ProjectMembership, Project
from src.projects.domain.vo import ProjectRole
from src.shared.domain.exceptions import NotFoundError
from src.shared.utils.time import current_datetime
from src.tasks.domain.vo import TaskStatus
from src.tasks.schemas import TaskCreate
from src.tasks.services import TaskService
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import Priority, TicketNumber

from .helpers import make_task


@pytest.fixture
def task_service(
        mock_session,
        fake_task_repo,
        fake_ticket_repo,
        fake_user_repo,
        fake_project_repo,
        fake_project_access_service,
        event_publisher,
):
    return TaskService(
        session=mock_session,
        task_repo=fake_task_repo,
        ticket_repo=fake_ticket_repo,
        user_repo=fake_user_repo,
        project_repo=fake_project_repo,
        project_access_service=fake_project_access_service,
        event_publisher=event_publisher,
    )


@pytest.fixture
def current_support_user():
    return CurrentUser(
        user_id=uuid4(),
        email="support.user@mail.com",
        role=UserRole.SUPPORT_AGENT,
    )


@pytest.fixture
async def created_project(fake_project_repo, fake_membership_repo, current_support_user):
    project = Project.create(
        name="Test project",
        key="TESTPRJ",
        created_by=uuid4(),
        counterparty_id=uuid4(),
    )
    await fake_project_repo.create(project)

    membership = ProjectMembership(
        project_id=project.id,
        user_id=current_support_user.user_id,
        project_role=ProjectRole.CONTRIBUTOR,
        added_by=uuid4(),
        added_at=current_datetime(),
    )
    await fake_membership_repo.create(membership)

    return project


@pytest.fixture
async def created_ticket(fake_ticket_repo, created_project):
    ticket = Ticket.create(
        ticket_number=TicketNumber("TESTPRJ-26-00000001"),
        title="Test ticket",
        description="This ticket created for test",
        reporter_id=uuid4(),
        created_by=uuid4(),
        created_by_role=UserRole.CUSTOMER,
        project_id=created_project.id,
        counterparty_id=created_project.counterparty_id,
    )
    await fake_ticket_repo.create(ticket)

    return ticket


class TestTaskCreate:

    @pytest.mark.asyncio
    async def test_create_internal_task_success(
            self, task_service, current_support_user, mock_session, fake_task_repo
    ):
        """
        Создание внутренней задачи (без проекта, без привязки к тикету)
        """

        data = TaskCreate(title="Тестовая задача", priority=Priority.MEDIUM)

        response = await task_service.create(data, current_support_user)

        assert response.title == "Тестовая задача"
        assert response.number == "TASK-001"
        assert response.status == TaskStatus.BACKLOG

        mock_session.commit.assert_awaited_once()

        created_task = await fake_task_repo.read(response.id)
        assert created_task is not None

    @pytest.mark.asyncio
    async def test_create_in_todo_with_ticket_and_project_success(
            self, task_service, current_support_user, created_ticket, created_project
    ):
        """
        Успешное создание готовой к выполнению задачи,
        привязанной к тикету + проверка определения проекта.
        """

        data = TaskCreate(
            ticket_id=created_ticket.id,
            title="Тестовая задача",
            priority=Priority.MEDIUM,
            mark_as_todo=True,
        )

        response = await task_service.create(data, current_support_user)

        assert response.project_id == created_project.id
        assert response.ticket_id == created_ticket.id
        assert response.status == TaskStatus.TODO
        assert response.number == f"{created_ticket.number}-001"

    @pytest.mark.asyncio
    async def test_create_raises_permission_denied(self, task_service, mock_session):
        """
        При недостаточных правах на создание должна выбрасываться ошибка
        """

        current_user = CurrentUser(
            user_id=uuid4(), email="customer.user@mail.com", role=UserRole.CUSTOMER
        )
        data = TaskCreate(title="Тестовая задача", priority=Priority.MEDIUM)

        with pytest.raises(PermissionDeniedError):
            await task_service.create(data, current_user)

        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_with_ticket_raises_not_found(
            self, task_service, current_support_user, mock_session
    ):
        """
        При передаче несуществующего тикета должна выбрасываться ошибка
        """

        data = TaskCreate(
            title="Тестовая задача", priority=Priority.MEDIUM, ticket_id=uuid4()
        )

        with pytest.raises(NotFoundError):
            await task_service.create(data, current_support_user)

        mock_session.commit.assert_not_awaited()


class TestMoveTo:

    @pytest.mark.asyncio
    async def test_move_to_valid_status_success(
            self, task_service, current_support_user, fake_task_repo, mock_session
    ):
        """
        Перевод задачи к новому статусу по её workflow
        """

        task = make_task(assignee_id=current_support_user.user_id, status=TaskStatus.TODO)
        await fake_task_repo.create(task)

        response = await task_service.change_status(
            task_id=task.id,
            new_status=TaskStatus.IN_PROGRESS,
            current_subject=current_support_user
        )

        assert response.status == TaskStatus.IN_PROGRESS
        assert response.updated_at > task.created_at
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_move_to_raises_permission_denied(
            self, task_service, current_support_user, fake_task_repo, mock_session
    ):
        """
        Пользователь без нужных прав не может менять статус задачи
        """

        task = make_task(status=TaskStatus.TODO)
        await fake_task_repo.create(task)

        with pytest.raises(PermissionDeniedError):
            await task_service.change_status(
                task_id=task.id,
                new_status=TaskStatus.IN_PROGRESS,
                current_subject=current_support_user
            )

        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_move_to_raises_not_found(
            self, task_service, current_support_user, mock_session
    ):
        """
        Нельзя изменить статус несуществующей задачи
        """

        with pytest.raises(NotFoundError):
            await task_service.change_status(
                task_id=uuid4(),
                new_status=TaskStatus.IN_PROGRESS,
                current_subject=current_support_user,
            )

        mock_session.commit.assert_not_awaited()
