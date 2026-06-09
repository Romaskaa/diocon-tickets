from decimal import Decimal
from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.services import create_finance, create_support
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import Project
from src.projects.domain.services import ProjectAccessService
from src.projects.domain.vo import ProjectRole
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.shared.domain.exceptions import InvalidStateError, NotFoundError
from src.shared.infra.events import EventBus
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import TaskNumber, TaskStatus
from src.tasks.infra.repos import SqlTaskRepository
from src.tasks.schemas import TaskCreate, TaskEdit, TaskReview
from src.tasks.services.task import TaskService
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import Priority, TicketNumber
from src.tickets.infra.repos import SqlTicketRepository


@pytest.fixture
def task_repo(session):
    return SqlTaskRepository(session)


@pytest.fixture
def ticket_repo(session):
    return SqlTicketRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
def project_access_service(membership_repo):
    return ProjectAccessService(membership_repo)


@pytest.fixture
def event_publisher():
    return EventBus(max_queue_size=10)


@pytest.fixture
def task_service(
    session,
    task_repo,
    ticket_repo,
    user_repo,
    project_repo,
    project_access_service,
    event_publisher,
):
    return TaskService(
        session=session,
        task_repo=task_repo,
        ticket_repo=ticket_repo,
        user_repo=user_repo,
        project_repo=project_repo,
        project_access_service=project_access_service,
        event_publisher=event_publisher
    )


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email=f"task-service-manager-{uuid4()}@example.com",
        role=UserRole.SUPPORT_MANAGER,
        counterparty_id=None,
    )


def make_project(owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name=f"Task Service Project {uuid4()}",
        key=f"TS{uuid4().hex[:6].upper()}",
        created_by=user_id,
        description="Project for task service integration test",
    )


def make_ticket(*, project_id=None, created_by=None) -> Ticket:
    user_id = created_by or uuid4()

    return Ticket.create(
        ticket_number=TicketNumber(f"TS-26-{uuid4().int % 10**8:08d}"),
        reporter_id=user_id,
        created_by=user_id,
        created_by_role=UserRole.SUPPORT_MANAGER,
        title=f"Task service ticket {uuid4()}",
        description="Ticket for task service integration test",
        project_id=project_id,
        priority=Priority.MEDIUM,
    )


def make_task_create(**overrides) -> TaskCreate:
    data = {
        "ticket_id": None,
        "project_id": None,
        "title": f"Task service task {uuid4()}",
        "description": "Task created through TaskService",
        "priority": Priority.MEDIUM,
        "story_points": None,
        "assignee_id": None,
        "reviewer_id": None,
        "estimated_hours": Decimal(2),
        "due_date": None,
        "tags": [],
        "mark_as_todo": False,
    }
    data.update(overrides)
    return TaskCreate(**data)


def make_current_user(
    *,
    role: UserRole = UserRole.SUPPORT_AGENT,
    user_id=None,
    counterparty_id=None,
) -> CurrentUser:
    return CurrentUser(
        user_id=user_id or uuid4(),
        email=f"task-service-user-{uuid4()}@example.com",
        role=role,
        counterparty_id=counterparty_id,
    )


@pytest.mark.asyncio
async def test_create_task_with_missing_ticket_returns_404(task_service, current_support_manager):
    """
    Проверка TaskService.create: если передан ticket_id, которого нет в бд,
    сервис должен вернуть NotFoundError.
    Данные: случайный ticket_id без сохранённого тикета.
    """

    missing_ticket_id = uuid4()
    data = make_task_create(ticket_id=missing_ticket_id)

    with pytest.raises(NotFoundError, match=f"Ticket with ID {missing_ticket_id} not found"):
        await task_service.create(data, current_user=current_support_manager)


@pytest.mark.asyncio
async def test_create_task_with_missing_project_returns_404(task_service, current_support_manager):
    """
    Проверка TaskService.create: если передан project_id, которого нет в БД,
    сервис должен вернуть NotFoundError.
    Данные: случайный project_id без сохранённого проекта.
    """

    missing_project_id = uuid4()
    data = make_task_create(project_id=missing_project_id)

    with pytest.raises(NotFoundError, match=f"Project with ID {missing_project_id} not found"):
        await task_service.create(data, current_user=current_support_manager)


@pytest.mark.asyncio
async def test_create_task_with_ticket_and_mismatched_project_returns_409(
    session,
    task_service,
    ticket_repo,
    project_repo,
    current_support_manager,
):
    """
    Проверка TaskService.create: если тикет принадлежит одному проекту,
    а в данных создания задачи передан другой project_id, сервис должен
    запретить создание задачи.
    Данные: два проекта и тикет, привязанный только к первому проекту.
    """

    ticket_project = make_project(owner_id=current_support_manager.user_id)
    another_project = make_project(owner_id=current_support_manager.user_id)

    ticket = make_ticket(
        project_id=ticket_project.id,
        created_by=current_support_manager.user_id,
    )

    await project_repo.create(ticket_project)
    await project_repo.create(another_project)
    await ticket_repo.create(ticket)
    await session.commit()

    data = make_task_create(
        ticket_id=ticket.id,
        project_id=another_project.id,
    )

    with pytest.raises(InvalidStateError, match="Project mismatch with ticket"):
        await task_service.create(data, current_user=current_support_manager)


@pytest.mark.asyncio
async def test_create_task_with_project_creates_project_number(
    session,
    task_service,
    task_repo,
    project_repo,
    membership_repo,
    current_support_manager,
):
    """
    Проверка TaskService.create: если задача создаётся внутри проекта,
    сервис должен создать номер задачи с ключом проекта и сохранить задачу в БД.
    Данные: проект, membership текущего пользователя и TaskCreate с project_id.
    """

    project = make_project(owner_id=current_support_manager.user_id)

    membership = project.create_membership(
        user_id=current_support_manager.user_id,
        project_role=ProjectRole.MANAGER,
        created_by=current_support_manager.user_id
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await session.commit()

    data = make_task_create(
        project_id=project.id,
        mark_as_todo=True,
    )

    response = await task_service.create(data, current_user=current_support_manager)
    created_task = await task_repo.read(response.id)

    assert response.project_id == project.id
    assert response.number.startswith(f"{project.key}-")
    assert response.status == TaskStatus.TODO

    assert created_task is not None
    assert created_task.project_id == project.id
    assert created_task.number.value == response.number
    assert created_task.status == TaskStatus.TODO


@pytest.mark.asyncio
async def test_create_task_denies_customer_user(task_service):
    """
    Проверяем TaskService.create: пользователь с ролью CUSTOMER не может
    создавать задачи.
    Данные: CurrentUser с ролью CUSTOMER и валидный TaskCreate без проекта и тикета.
    """

    customer_user = CurrentUser(
        user_id=uuid4(),
        email=f"task-service-customer-{uuid4()}@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=uuid4(),
    )

    data = make_task_create()

    with pytest.raises(PermissionDeniedError):
        await task_service.create(data, current_user=customer_user)


@pytest.mark.asyncio
async def test_edit_task_denies_not_creator_or_assignee(session, task_service, task_repo):
    """
    Проверяем TaskService.editЖ support-пользователь не может редактировать задачу,
    если он не является ни создатеелем, ни испольнителем.
    Данные: задача, созданная одним пользователем, и другой support-agent.
    """

    creator_id = uuid4()
    assignee_id = uuid4()

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service edit denied {uuid4()}",
        description="Task for edit permission integration test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        assignee_id=assignee_id,
        actual_hours=Decimal(0),
        created_by=creator_id,
    )

    await task_repo.create(task)
    await session.commit()

    another_support_user = CurrentUser(
        user_id=uuid4(),
        email=f"task-service-editor-{uuid4()}@example.com",
        role=UserRole.SUPPORT_AGENT,
        counterparty_id=None,
    )

    data = TaskEdit(
        title="Updated title",
        description="Updated description",
        priority=Priority.HIGH,
        story_points=5,
        estimated_hours=4,
        due_date=None,
    )

    with pytest.raises(PermissionDeniedError):
        await task_service.edit(
            task_id=task.id,
            data=data,
            current_user=another_support_user,
        )

    unchanged_task = await task_repo.read(task.id)

    assert unchanged_task is not None
    assert unchanged_task.title == task.title
    assert unchanged_task.description == task.description
    assert unchanged_task.priority == Priority.MEDIUM


@pytest.mark.asyncio
async def test_create_task_with_ticket_uses_ticket_project(
    session,
    task_service,
    task_repo,
    ticket_repo,
    project_repo,
    membership_repo,
    current_support_manager,
):
    """
    Проверка TaskService.create: если задача создаётся по тикету,
    у которого есть project_id, сервис должен взять project_id из тикета.
    Данные: проект, membership текущего пользователя и тикет внтури проекта.
    """

    project = make_project(owner_id=current_support_manager.user_id)

    membership = project.create_membership(
        user_id=current_support_manager.user_id,
        project_role=ProjectRole.MANAGER,
        created_by=current_support_manager.user_id,
    )

    ticket = make_ticket(
        project_id=project.id,
        created_by=current_support_manager.user_id,
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await ticket_repo.create(ticket)
    await session.commit()

    data = make_task_create(
        ticket_id=ticket.id,
        project_id=None,
    )

    response = await task_service.create(data, current_user=current_support_manager)
    created_task = await task_repo.read(response.id)

    assert response.ticket_id == ticket.id
    assert response.project_id == project.id
    assert response.number.startswith(str(ticket.number))

    assert created_task is not None
    assert created_task.ticket_id == ticket.id
    assert created_task.project_id == project.id


@pytest.mark.asyncio
async def test_create_task_denies_project_viewer(
    session,
    task_service,
    project_repo,
    membership_repo,
    current_support_manager,
):
    """
    Проверка TaskService.create: участник проекта с ролью VIEWER
    не может создавать задачи внтури проекта.
    Данные: проект и memebership текщуего пользователя с ProjectRole.VIEWER
    """

    project = make_project(owner_id=uuid4())

    membership = project.create_membership(
        user_id=current_support_manager.user_id,
        project_role=ProjectRole.VIEWER,
        created_by=project.created_by,
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await session.commit()

    data = make_task_create(project_id=project.id)

    with pytest.raises(PermissionDeniedError):
        await task_service.create(data, current_user=current_support_manager)


@pytest.mark.asyncio
async def test_assign_task_denies_non_support_assignee(
    session,
    task_service,
    task_repo,
    user_repo,
    current_support_manager,
):
    """
    Проверяем TaskService.assign_to: задачу нельзя назначить на пользователя
    с неподходящей внутренней ролью.
    Данные: существующая задача и finance-пользователь в БД.
    """

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service assign denied {uuid4()}",
        description="Task for assign permission integration test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        actual_hours=Decimal(0),
        created_by=current_support_manager.user_id,
    )

    assignee = create_finance(
        email=f"task-finance-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
    )

    await task_repo.create(task)
    await user_repo.create(assignee)
    await session.commit()

    with pytest.raises(PermissionDeniedError):
        await task_service.assign_to(
            task_id=task.id,
            assignee_id=assignee.id,
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_request_review_denies_finance_reviewer(session, task_service, task_repo, user_repo):
    """
    Проверка TaskService.request_review: ревью нельзя запросить у пользователя
    с неподходящей ролью.
    Данные: IN_PROGRESS-задача и finance-пользователь в БД.
    """

    requester = CurrentUser(
        user_id=uuid4(),
        email=f"task-service-requester-{uuid4()}@example.com",
        role=UserRole.SUPPORT_AGENT,
        counterparty_id=None,
    )

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service review denied {uuid4()}",
        description="Task for review permission integration test",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=requester.user_id,
        actual_hours=Decimal(0),
        created_by=requester.user_id,
    )

    task.move_to(
        new_status=TaskStatus.IN_PROGRESS,
        moved_by=requester.user_id,
    )

    reviewer = create_finance(
        email=f"task-service-reviewer-finance-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
    )

    await task_repo.create(task)
    await user_repo.create(reviewer)
    await session.commit()

    with pytest.raises(PermissionDeniedError):
        await task_service.request_review(
            task_id=task.id,
            reviewer_id=reviewer.id,
            current_user=requester,
        )


@pytest.mark.asyncio
async def test_assign_task_returns_task_with_assignee(
    session,
    task_service,
    task_repo,
    user_repo,
    current_support_manager,
):
    """
    Проверка TaskService.assign_to: задачу можно назначить на support-пользователя.
    Данные: существующая задача без испольнителя и support-agent в БД.
    """

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service assign {uuid4()}",
        description="Task for assign integration test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        actual_hours=Decimal(0),
        created_by=current_support_manager.user_id,
    )

    assignee = create_support(
        email=f"task-service-assignee-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        user_role=UserRole.SUPPORT_AGENT,
    )

    await task_repo.create(task)
    await user_repo.create(assignee)
    await session.commit()

    response = await task_service.assign_to(
        task_id=task.id,
        assignee_id=assignee.id,
        current_user=current_support_manager,
    )

    updated_task = await task_repo.read(task.id)

    assert response.id == task.id
    assert response.assignee_id == assignee.id

    assert updated_task is not None
    assert updated_task.assignee_id == assignee.id


@pytest.mark.asyncio
async def test_request_review_returns_review_task(session, task_service, task_repo, user_repo):
    """
    Проверка TaskService.request_review: исполнитель может запросить ревью у support-manager.
    Данные: IN-PROGRESS-задача, где текущий пользователь является испольнителем.
    """

    requester = make_current_user(role=UserRole.SUPPORT_AGENT)

    reviewer = create_support(
        email=f"task-service-reviewer-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        user_role=UserRole.SUPPORT_MANAGER,
    )

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service request review {uuid4()}",
        description="Task for request review integration test",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=requester.user_id,
        actual_hours=Decimal(0),
        created_by=requester.user_id,
    )
    task.move_to(TaskStatus.IN_PROGRESS, moved_by=requester.user_id)

    await task_repo.create(task)
    await user_repo.create(reviewer)
    await session.commit()

    response = await task_service.request_review(
        task_id=task.id,
        reviewer_id=reviewer.id,
        current_user=requester,
    )

    updated_task = await task_repo.read(task.id)

    assert response.id == task.id
    assert response.reviewer_id == reviewer.id
    assert response.status == TaskStatus.REVIEW

    assert updated_task is not None
    assert updated_task.reviewer_id == reviewer.id
    assert updated_task.status == TaskStatus.REVIEW


@pytest.mark.asyncio
async def test_request_review_missing_reviewer_returns_404(session, task_service, task_repo):
    """
    Проверяем TaskService.request_review: если reviewer отсутствует в БД,
    сервис возвращает NotFoundError.
    Данные: IN_PROGRESS-задача и случайный reviewer_id без пользователя.
    """

    requester = make_current_user(role=UserRole.SUPPORT_AGENT)
    missing_reviewer_id = uuid4()

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service missing reviewer {uuid4()}",
        description="Task for missing reviewer integration test",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=requester.user_id,
        actual_hours=Decimal(0),
        created_by=requester.user_id,
    )
    task.move_to(TaskStatus.IN_PROGRESS, moved_by=requester.user_id)

    await task_repo.create(task)
    await session.commit()

    with pytest.raises(
        NotFoundError,
        match=f"Reviewer with ID {missing_reviewer_id} not found",
    ):
        await task_service.request_review(
            task_id=task.id,
            reviewer_id=missing_reviewer_id,
            current_user=requester,
        )


@pytest.mark.asyncio
async def test_move_task_returns_task_with_new_status(session, task_service, task_repo):
    """
    Проверяем TaskService.move_to: исполнитель задачи может перевести её в новый статус.
    Данные: TODO-задача, где текущий support-agent является исполнителем.
    """

    assignee = make_current_user(role=UserRole.SUPPORT_AGENT)

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service move {uuid4()}",
        description="Task for move status integration test",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=assignee.user_id,
        actual_hours=Decimal(0),
        created_by=assignee.user_id,
    )

    await task_repo.create(task)
    await session.commit()

    response = await task_service.move_to(
        task_id=task.id,
        new_status=TaskStatus.IN_PROGRESS,
        current_user=assignee,
    )

    updated_task = await task_repo.read(task.id)

    assert response.id == task.id
    assert response.status == TaskStatus.IN_PROGRESS
    assert response.started_at is not None

    assert updated_task is not None
    assert updated_task.status == TaskStatus.IN_PROGRESS
    assert updated_task.started_at is not None


@pytest.mark.asyncio
async def test_move_task_denies_not_assignee(session, task_service, task_repo):
    """
    Проверяем TaskService.move_to: support-agent не может менять статус чужой задачи.
    Данные: TODO-задача назначена одному пользователю, действие выполняет другой support-agent.
    """

    assignee_id = uuid4()
    another_user = make_current_user(role=UserRole.SUPPORT_AGENT)

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service move denied {uuid4()}",
        description="Task for move status permission integration test",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=assignee_id,
        actual_hours=Decimal(0),
        created_by=assignee_id,
    )

    await task_repo.create(task)
    await session.commit()

    with pytest.raises(PermissionDeniedError):
        await task_service.move_to(
            task_id=task.id,
            new_status=TaskStatus.IN_PROGRESS,
            current_user=another_user,
        )

    unchanged_task = await task_repo.read(task.id)

    assert unchanged_task is not None
    assert unchanged_task.status == TaskStatus.TODO
    assert unchanged_task.started_at is None


@pytest.mark.asyncio
async def test_review_task_approve_returns_done(session, task_service, task_repo):
    """
    Проверяем TaskService.review: approve переводит задачу из REVIEW в DONE.
    Данные: REVIEW-задача, где текущий support-manager является reviewer.
    """

    assignee_id = uuid4()
    reviewer = make_current_user(role=UserRole.SUPPORT_MANAGER)

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service approve review {uuid4()}",
        description="Task for approve review integration test",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=assignee_id,
        actual_hours=Decimal(0),
        created_by=assignee_id,
    )
    task.move_to(TaskStatus.IN_PROGRESS, moved_by=assignee_id)
    task.request_review(
        reviewer_id=reviewer.user_id,
        requested_by=assignee_id,
    )

    await task_repo.create(task)
    await session.commit()

    response = await task_service.review(
        task_id=task.id,
        data=TaskReview(action="approve"),
        current_user=reviewer,
    )

    updated_task = await task_repo.read(task.id)

    assert response.id == task.id
    assert response.status == TaskStatus.DONE
    assert response.completed_at is not None

    assert updated_task is not None
    assert updated_task.status == TaskStatus.DONE
    assert updated_task.completed_at is not None


@pytest.mark.asyncio
async def test_review_task_reject_returns_in_progress(session, task_service, task_repo):
    """
    Проверяем TaskService.review: reject возвращает задачу из REVIEW в IN_PROGRESS.
    Данные: REVIEW-задача, где текущий support-manager является reviewer.
    """

    assignee_id = uuid4()
    reviewer = make_current_user(role=UserRole.SUPPORT_MANAGER)

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service reject review {uuid4()}",
        description="Task for reject review integration test",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=assignee_id,
        actual_hours=Decimal(0),
        created_by=assignee_id,
    )
    task.move_to(TaskStatus.IN_PROGRESS, moved_by=assignee_id)
    task.request_review(
        reviewer_id=reviewer.user_id,
        requested_by=assignee_id,
    )

    await task_repo.create(task)
    await session.commit()

    response = await task_service.review(
        task_id=task.id,
        data=TaskReview(action="reject"),
        current_user=reviewer,
    )

    updated_task = await task_repo.read(task.id)

    assert response.id == task.id
    assert response.status == TaskStatus.IN_PROGRESS

    assert updated_task is not None
    assert updated_task.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_review_task_denies_not_reviewer(session, task_service, task_repo):
    """
    Проверяем TaskService.review: пользователь, который не является reviewer,
    не может провести ревью задачи.
    Данные: REVIEW-задача с одним reviewer и другой support-agent как текущий пользователь.
    """

    assignee_id = uuid4()
    reviewer_id = uuid4()
    another_user = make_current_user(role=UserRole.SUPPORT_AGENT)

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service review denied {uuid4()}",
        description="Task for review permission integration test",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=assignee_id,
        actual_hours=Decimal(0),
        created_by=assignee_id,
    )
    task.move_to(TaskStatus.IN_PROGRESS, moved_by=assignee_id)
    task.request_review(
        reviewer_id=reviewer_id,
        requested_by=assignee_id,
    )

    await task_repo.create(task)
    await session.commit()

    with pytest.raises(PermissionDeniedError):
        await task_service.review(
            task_id=task.id,
            data=TaskReview(action="approve"),
            current_user=another_user,
        )

    unchanged_task = await task_repo.read(task.id)

    assert unchanged_task is not None
    assert unchanged_task.status == TaskStatus.REVIEW
    assert unchanged_task.completed_at is None


@pytest.mark.asyncio
async def test_archive_task_by_creator_marks_task_archived(
    session,
    task_service,
    task_repo,
    current_support_manager,
):
    """
    Проверяем TaskService.archive: создатель задачи может отправить её в архив.
    Данные: существующая BACKLOG-задача, созданная текущим support-manager.
    """

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service archive {uuid4()}",
        description="Task for archive integration test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        actual_hours=Decimal(0),
        created_by=current_support_manager.user_id,
    )

    await task_repo.create(task)
    await session.commit()

    response = await task_service.archive(
        task_id=task.id,
        current_user=current_support_manager,
    )

    archived_task = await task_repo.read(task.id)

    assert response.id == task.id
    assert response.is_archived is True

    assert archived_task is not None
    assert archived_task.is_deleted is True
    assert archived_task.deleted_at is not None


@pytest.mark.asyncio
async def test_archive_task_denies_not_creator(session, task_service, task_repo):
    """
    Проверяем TaskService.archive: пользователь не может архивировать чужую задачу.
    Данные: задача создана одним пользователем, архивировать пытается другой support-agent.
    """

    creator_id = uuid4()
    another_user = make_current_user(role=UserRole.SUPPORT_AGENT)

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service archive denied {uuid4()}",
        description="Task for archive permission integration test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        actual_hours=Decimal(0),
        created_by=creator_id,
    )

    await task_repo.create(task)
    await session.commit()

    with pytest.raises(PermissionDeniedError):
        await task_service.archive(
            task_id=task.id,
            current_user=another_user,
        )

    unchanged_task = await task_repo.read(task.id)

    assert unchanged_task is not None
    assert unchanged_task.is_deleted is False
    assert unchanged_task.deleted_at is None


@pytest.mark.asyncio
async def test_add_actual_hours_updates_task(
    session,
    task_service,
    task_repo,
    current_support_manager,
):
    """
    Проверяем TaskService.add_actual_hours: фактические часы добавляются
    к задаче и сохраняются в БД.
    Данные: существующая задача с actual_hours = 0.
    """

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service actual hours {uuid4()}",
        description="Task for actual hours integration test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        actual_hours=Decimal(0),
        created_by=current_support_manager.user_id,
    )

    await task_repo.create(task)
    await session.commit()

    await task_service.add_actual_hours(
        task_id=task.id,
        hours=Decimal("2.5"),
    )

    updated_task = await task_repo.read(task.id)

    assert updated_task is not None
    assert updated_task.actual_hours == Decimal("2.5")


@pytest.mark.asyncio
async def test_add_actual_hours_missing_task_returns_404(task_service):
    """
    Проверяем TaskService.add_actual_hours: если задачи нет в БД, сервис возвращает NotFoundError.
    Данные: случайный task_id без сохранённой задачи.
    """

    missing_task_id = uuid4()

    with pytest.raises(NotFoundError, match=f"Task with ID {missing_task_id} not found"):
        await task_service.add_actual_hours(
            task_id=missing_task_id,
            hours=Decimal("1.5"),
        )
