from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.projects.domain.entities import Project
from src.projects.domain.services import ProjectAccessService
from src.projects.domain.vo import ProjectRole
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import TicketNumber, TicketStatus


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)


@pytest.fixture
def access_service(membership_repo):
    return ProjectAccessService(membership_repo)


def make_project(owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name=f"Access Project {uuid4()}",
        key=f"AC{uuid4().hex[:6].upper()}",
        description="Project for access integration tests",
        created_by=user_id,
    )


def make_ticket(
    *,
    status: TicketStatus = TicketStatus.OPEN,
    counterparty_id=None,
) -> Ticket:
    ticket = Ticket.create(
        ticket_number=TicketNumber("INT-26-00000001"),
        reporter_id=uuid4(),
        created_by=uuid4(),
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Access check ticket",
        project_id=uuid4(),
        counterparty_id=counterparty_id,
    )
    ticket.status = status
    list(ticket.collect_events())
    return ticket


async def create_membership(
    session,
    project_repo,
    membership_repo,
    project: Project,
    *,
    user_id,
    project_role: ProjectRole,
):
    membership = project.create_membership(
        user_id=user_id,
        project_role=project_role,
        created_by=project.owner_id,
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await session.commit()

    return membership


@pytest.mark.asyncio
async def test_transfer_ownership_allows_current_owner_to_transfer_to_internal_member(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем передачу владения проектом: текущий OWNER может передать проект
    другому внутреннему участнику проекта.
    Данные: проект в реальной БД и membership нового владельца с ролью MANAGER.
    """

    owner_id = uuid4()
    new_owner_id = uuid4()
    project = make_project(owner_id=owner_id)
    owner_membership = project.create_membership(
        user_id=owner_id,
        project_role=ProjectRole.OWNER,
        created_by=owner_id,
    )
    new_owner_membership = project.create_membership(
        user_id=new_owner_id,
        project_role=ProjectRole.MANAGER,
        created_by=owner_id,
    )

    await project_repo.create(project)
    await membership_repo.create(owner_membership)
    await membership_repo.create(new_owner_membership)
    await session.commit()

    permission = await access_service.can_transfer_ownership(
        project=project,
        target_user_id=new_owner_id,
        user_id=owner_id,
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_transfer_ownership_rejects_missing_target_member(access_service):
    """
    Проверяем передачу владения проектом: нельзя передать проект пользователю,
    которого нет среди участников проекта.
    Данные: проект без membership для target_user_id.
    """

    owner_id = uuid4()
    project = make_project(owner_id=owner_id)

    permission = await access_service.can_transfer_ownership(
        project=project,
        target_user_id=uuid4(),
        user_id=owner_id,
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is False
    assert permission.reason == "Target owner dose not exist"


@pytest.mark.asyncio
async def test_transfer_ownership_rejects_transfer_to_self(access_service):
    """
    Проверяем передачу владения проектом: владелец не должен передавать проект
    самому себе.
    Данные: проект и один user_id, который одновременно текущий владелец и target.
    """

    owner_id = uuid4()
    project = make_project(owner_id=owner_id)

    permission = await access_service.can_transfer_ownership(
        project=project,
        target_user_id=owner_id,
        user_id=owner_id,
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is False
    assert permission.reason == "You are already the owner"


@pytest.mark.asyncio
async def test_transfer_ownership_rejects_customer_member(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем передачу владения проектом: клиентский участник не может стать
    владельцем проекта.
    Данные: проект в реальной БД и target membership с ролью CUSTOMER.
    """

    owner_id = uuid4()
    customer_id = uuid4()
    project = make_project(owner_id=owner_id)
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=customer_id,
        project_role=ProjectRole.CUSTOMER,
    )

    permission = await access_service.can_transfer_ownership(
        project=project,
        target_user_id=customer_id,
        user_id=owner_id,
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is False
    assert permission.reason == "Cannot transfer ownership to a customer"


@pytest.mark.asyncio
async def test_admin_can_transfer_ownership_without_owner_membership(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем передачу владения проектом: системный ADMIN может передать проект
    целевому внутреннему участнику, даже если сам не состоит в проекте.
    Данные: проект и target membership MANAGER в реальной БД.
    """

    admin_id = uuid4()
    target_id = uuid4()
    project = make_project(owner_id=uuid4())
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=target_id,
        project_role=ProjectRole.MANAGER,
    )

    permission = await access_service.can_transfer_ownership(
        project=project,
        target_user_id=target_id,
        user_id=admin_id,
        user_role=UserRole.ADMIN,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_manager_member_cannot_transfer_ownership(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем передачу владения проектом: MANAGER может управлять проектом,
    но не должен передавать владение, потому что это право OWNER или ADMIN.
    Данные: проект, manager membership и target membership CONTRIBUTOR в реальной БД.
    """

    manager_id = uuid4()
    target_id = uuid4()
    project = make_project(owner_id=uuid4())
    manager_membership = project.create_membership(
        user_id=manager_id,
        project_role=ProjectRole.MANAGER,
        created_by=project.owner_id,
    )
    target_membership = project.create_membership(
        user_id=target_id,
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=project.owner_id,
    )

    await project_repo.create(project)
    await membership_repo.create(manager_membership)
    await membership_repo.create(target_membership)
    await session.commit()

    permission = await access_service.can_transfer_ownership(
        project=project,
        target_user_id=target_id,
        user_id=manager_id,
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is False
    assert permission.reason == "Only the project owner or admin can transfer ownership"


@pytest.mark.asyncio
async def test_viewer_member_cannot_add_members(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем добавление участников: VIEWER состоит в проекте, но не имеет
    права добавлять новых участников.
    Данные: проект и viewer membership в реальной БД.
    """

    viewer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=viewer_id,
        project_role=ProjectRole.VIEWER,
    )

    permission = await access_service.can_add_members(
        project=project,
        target_user_role=UserRole.SUPPORT_AGENT,
        target_project_role=ProjectRole.CONTRIBUTOR,
        user_id=viewer_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert permission.reason == "You do not have permission to add members"


@pytest.mark.asyncio
async def test_support_manager_can_create_ticket_without_membership(access_service):
    """
    Проверяем создание тикета в проекте: SUPPORT_MANAGER может создавать тикеты
    без проверки membership.
    Данные: случайный project_id без записи membership в БД.
    """

    permission = await access_service.can_create_ticket(
        project_id=uuid4(),
        user_id=uuid4(),
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_viewer_member_cannot_create_ticket(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем создание тикета в проекте: VIEWER является участником проекта,
    но не должен иметь право создавать тикеты.
    Данные: проект и viewer membership в реальной БД.
    """

    viewer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=viewer_id,
        project_role=ProjectRole.VIEWER,
    )

    permission = await access_service.can_create_ticket(
        project_id=project.id,
        user_id=viewer_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert permission.reason == "You do not have permission to create ticket"


@pytest.mark.asyncio
async def test_active_project_member_can_view_ticket(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем просмотр тикетов проекта: любой активный участник проекта может
    смотреть тикеты этого проекта.
    Данные: проект и viewer membership в реальной БД.
    """

    viewer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=viewer_id,
        project_role=ProjectRole.VIEWER,
    )

    permission = await access_service.can_view_ticket(
        project_id=project.id,
        user_id=viewer_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_support_manager_can_view_ticket_without_membership(access_service):
    """
    Проверяем просмотр тикетов проекта: SUPPORT_MANAGER может смотреть тикеты
    без membership в конкретном проекте.
    Данные: случайный project_id без записи membership в БД.
    """

    permission = await access_service.can_view_ticket(
        project_id=uuid4(),
        user_id=uuid4(),
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_support_manager_can_assign_ticket_without_membership(access_service):
    """
    Проверяем назначение тикета: SUPPORT_MANAGER может назначать тикеты без
    membership в конкретном проекте.
    Данные: случайные project_id, assignee_id и user_id без записей membership.
    """

    permission = await access_service.can_assign_ticket(
        project_id=uuid4(),
        assignee_id=uuid4(),
        user_id=uuid4(),
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_assign_ticket_rejects_non_member(access_service):
    """
    Проверяем назначение тикета: пользователь, которого нет среди участников
    проекта, не может назначать тикеты.
    Данные: случайный project_id без membership для user_id.
    """

    permission = await access_service.can_assign_ticket(
        project_id=uuid4(),
        assignee_id=uuid4(),
        user_id=uuid4(),
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert permission.reason == "Your not member of this project"


@pytest.mark.asyncio
async def test_viewer_member_cannot_assign_ticket(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем назначение тикета: VIEWER состоит в проекте, но не имеет
    проектной роли, позволяющей назначать тикеты.
    Данные: проект и viewer membership в реальной БД.
    """

    viewer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=viewer_id,
        project_role=ProjectRole.VIEWER,
    )

    permission = await access_service.can_assign_ticket(
        project_id=project.id,
        assignee_id=uuid4(),
        user_id=viewer_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert "Only members with project roles can assign tickets" in permission.reason


@pytest.mark.asyncio
async def test_assign_ticket_rejects_target_viewer(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем назначение тикета: назначать тикет можно только на внутреннего
    исполнителя, а не на viewer/customer-роль.
    Данные: проект, contributor-инициатор и viewer-цель в реальной БД.
    """

    actor_id = uuid4()
    viewer_id = uuid4()
    project = make_project()
    actor_membership = project.create_membership(
        user_id=actor_id,
        project_role=ProjectRole.CONTRIBUTOR,
        created_by=project.owner_id,
    )
    viewer_membership = project.create_membership(
        user_id=viewer_id,
        project_role=ProjectRole.VIEWER,
        created_by=project.owner_id,
    )

    await project_repo.create(project)
    await membership_repo.create(actor_membership)
    await membership_repo.create(viewer_membership)
    await session.commit()

    permission = await access_service.can_assign_ticket(
        project_id=project.id,
        assignee_id=viewer_id,
        user_id=actor_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert permission.reason == "Cannot assign a ticket to a CLIENT_* or VIEWER"


@pytest.mark.asyncio
async def test_assign_ticket_rejects_missing_target_member(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем назначение тикета: нельзя назначить тикет на пользователя,
    которого нет среди участников проекта.
    Данные: проект и contributor-инициатор в реальной БД, target_user_id отсутствует.
    """

    actor_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=actor_id,
        project_role=ProjectRole.CONTRIBUTOR,
    )

    permission = await access_service.can_assign_ticket(
        project_id=project.id,
        assignee_id=uuid4(),
        user_id=actor_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert permission.reason == "Target member dose not exist in this project"


@pytest.mark.asyncio
async def test_contributor_cannot_approve_ticket(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем смену статуса тикета: CONTRIBUTOR не может согласовывать тикет,
    который находится на согласовании.
    Данные: project membership CONTRIBUTOR и тикет со статусом PENDING_APPROVAL.
    """

    contributor_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=contributor_id,
        project_role=ProjectRole.CONTRIBUTOR,
    )
    ticket = make_ticket(status=TicketStatus.PENDING_APPROVAL)

    permission = await access_service.can_change_ticket_status(
        project_id=project.id,
        ticket=ticket,
        new_status=TicketStatus.OPEN,
        user_id=contributor_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert permission.reason == "CONTRIBUTOR cannot approve ticket"


@pytest.mark.asyncio
async def test_support_manager_can_change_ticket_status_without_membership(access_service):
    """
    Проверяем смену статуса тикета: SUPPORT_MANAGER может менять статус тикета
    без membership в конкретном проекте.
    Данные: случайный project_id и обычный тикет.
    """

    ticket = make_ticket(status=TicketStatus.OPEN)

    permission = await access_service.can_change_ticket_status(
        project_id=uuid4(),
        ticket=ticket,
        new_status=TicketStatus.IN_PROGRESS,
        user_id=uuid4(),
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_owner_member_can_change_ticket_status(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем смену статуса тикета: OWNER внутри проекта может менять любые
    статусы тикета.
    Данные: проект, owner membership и тикет в статусе OPEN.
    """

    owner_id = uuid4()
    project = make_project(owner_id=owner_id)
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=owner_id,
        project_role=ProjectRole.OWNER,
    )
    ticket = make_ticket(status=TicketStatus.OPEN)

    permission = await access_service.can_change_ticket_status(
        project_id=project.id,
        ticket=ticket,
        new_status=TicketStatus.IN_PROGRESS,
        user_id=owner_id,
        user_role=UserRole.SUPPORT_MANAGER,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_contributor_cannot_change_ticket_to_rejected(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем смену статуса тикета: CONTRIBUTOR может вести рабочие статусы,
    но не может переводить тикет в REJECTED.
    Данные: contributor membership и тикет в статусе OPEN.
    """

    contributor_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=contributor_id,
        project_role=ProjectRole.CONTRIBUTOR,
    )
    ticket = make_ticket(status=TicketStatus.OPEN)

    permission = await access_service.can_change_ticket_status(
        project_id=project.id,
        ticket=ticket,
        new_status=TicketStatus.REJECTED,
        user_id=contributor_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert "Insufficient rights to change to the next status" in permission.reason


@pytest.mark.asyncio
async def test_customer_manager_can_approve_own_counterparty_ticket(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем смену статуса тикета: CUSTOMER_MANAGER может согласовать тикет
    своего контрагента.
    Данные: customer-manager membership и тикет того же counterparty_id.
    """

    counterparty_id = uuid4()
    customer_manager_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=customer_manager_id,
        project_role=ProjectRole.CUSTOMER_MANAGER,
    )
    ticket = make_ticket(
        status=TicketStatus.PENDING_APPROVAL,
        counterparty_id=counterparty_id,
    )

    permission = await access_service.can_change_ticket_status(
        project_id=project.id,
        ticket=ticket,
        new_status=TicketStatus.OPEN,
        user_id=customer_manager_id,
        user_role=UserRole.CUSTOMER_ADMIN,
        user_counterparty_id=counterparty_id,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_viewer_member_cannot_change_ticket_status(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем смену статуса тикета: VIEWER состоит в проекте, но не попадает
    ни в одну роль, которой разрешена смена статуса.
    Данные: viewer membership и тикет в статусе OPEN.
    """

    viewer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=viewer_id,
        project_role=ProjectRole.VIEWER,
    )
    ticket = make_ticket(status=TicketStatus.OPEN)

    permission = await access_service.can_change_ticket_status(
        project_id=project.id,
        ticket=ticket,
        new_status=TicketStatus.IN_PROGRESS,
        user_id=viewer_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False


@pytest.mark.asyncio
async def test_customer_cannot_change_other_counterparty_ticket(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем смену статуса тикета: клиент не может менять тикеты чужого
    контрагента.
    Данные: customer membership и тикет с другим counterparty_id.
    """

    customer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=customer_id,
        project_role=ProjectRole.CUSTOMER,
    )
    ticket = make_ticket(status=TicketStatus.RESOLVED, counterparty_id=uuid4())

    permission = await access_service.can_change_ticket_status(
        project_id=project.id,
        ticket=ticket,
        new_status=TicketStatus.REOPENED,
        user_id=customer_id,
        user_role=UserRole.CUSTOMER,
        user_counterparty_id=uuid4(),
    )

    assert permission.allowed is False
    assert permission.reason == "You can only change tickets of your own counterparty"


@pytest.mark.asyncio
async def test_customer_cannot_approve_own_counterparty_ticket(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем смену статуса тикета: обычный CUSTOMER может переоткрывать свой
    тикет, но не может согласовывать его из PENDING_APPROVAL.
    Данные: customer membership и тикет того же counterparty_id на согласовании.
    """

    counterparty_id = uuid4()
    customer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=customer_id,
        project_role=ProjectRole.CUSTOMER,
    )
    ticket = make_ticket(
        status=TicketStatus.PENDING_APPROVAL,
        counterparty_id=counterparty_id,
    )

    permission = await access_service.can_change_ticket_status(
        project_id=project.id,
        ticket=ticket,
        new_status=TicketStatus.OPEN,
        user_id=customer_id,
        user_role=UserRole.CUSTOMER,
        user_counterparty_id=counterparty_id,
    )

    assert permission.allowed is False
    assert permission.reason == "Only CUSTOMER_MANAGER can approve tickets in own counterparty"


@pytest.mark.asyncio
async def test_customer_can_reopen_own_counterparty_ticket(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем смену статуса тикета: клиент может переоткрыть тикет своего
    контрагента.
    Данные: customer membership и тикет с тем же counterparty_id.
    """

    counterparty_id = uuid4()
    customer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=customer_id,
        project_role=ProjectRole.CUSTOMER,
    )
    ticket = make_ticket(status=TicketStatus.RESOLVED, counterparty_id=counterparty_id)

    permission = await access_service.can_change_ticket_status(
        project_id=project.id,
        ticket=ticket,
        new_status=TicketStatus.REOPENED,
        user_id=customer_id,
        user_role=UserRole.CUSTOMER,
        user_counterparty_id=counterparty_id,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_admin_can_create_task_without_membership(access_service):
    """
    Проверяем создание задач: ADMIN может создавать задачи без membership
    в конкретном проекте.
    Данные: случайный project_id без записей membership.
    """

    permission = await access_service.can_create_task(
        project_id=uuid4(),
        user_id=uuid4(),
        user_role=UserRole.ADMIN,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_non_member_cannot_create_task(access_service):
    """
    Проверяем создание задач: пользователь без membership не может создавать
    задачи внутри проекта.
    Данные: случайный project_id без membership для user_id.
    """

    permission = await access_service.can_create_task(
        project_id=uuid4(),
        user_id=uuid4(),
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert permission.reason == "Your not member of this project"


@pytest.mark.asyncio
async def test_customer_member_cannot_create_task(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем создание задач: клиентский участник проекта не должен создавать
    внутренние задачи.
    Данные: project membership с ролью CUSTOMER в реальной БД.
    """

    customer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=customer_id,
        project_role=ProjectRole.CUSTOMER,
    )

    permission = await access_service.can_create_task(
        project_id=project.id,
        user_id=customer_id,
        user_role=UserRole.CUSTOMER,
    )

    assert permission.allowed is False
    assert permission.reason == "Only members with role CONTRIBUTOR or above can create task"


@pytest.mark.asyncio
async def test_admin_can_view_tasks_without_membership(access_service):
    """
    Проверяем просмотр задач: ADMIN может смотреть задачи без membership
    в конкретном проекте.
    Данные: случайный project_id без записей membership.
    """

    permission = await access_service.can_view_tasks(
        project_id=uuid4(),
        user_id=uuid4(),
        user_role=UserRole.ADMIN,
    )

    assert permission.allowed is True


@pytest.mark.asyncio
async def test_non_member_cannot_view_tasks(access_service):
    """
    Проверяем просмотр задач: пользователь без membership не может смотреть
    задачи проекта.
    Данные: случайный project_id без membership для user_id.
    """

    permission = await access_service.can_view_tasks(
        project_id=uuid4(),
        user_id=uuid4(),
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is False
    assert permission.reason == "Your not member of this project"


@pytest.mark.asyncio
async def test_customer_member_cannot_view_tasks(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем просмотр задач: клиентский участник проекта не должен видеть
    внутреннюю доску задач.
    Данные: project membership с ролью CUSTOMER в реальной БД.
    """

    customer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=customer_id,
        project_role=ProjectRole.CUSTOMER,
    )

    permission = await access_service.can_view_tasks(
        project_id=project.id,
        user_id=customer_id,
        user_role=UserRole.CUSTOMER,
    )

    assert permission.allowed is False
    assert permission.reason == "Only members with role CONTRIBUTOR or above can view tasks"


@pytest.mark.asyncio
async def test_viewer_member_can_view_tasks(
    session,
    project_repo,
    membership_repo,
    access_service,
):
    """
    Проверяем просмотр задач: viewer не может создавать задачи, но может
    просматривать доску задач проекта.
    Данные: project membership с ролью VIEWER в реальной БД.
    """

    viewer_id = uuid4()
    project = make_project()
    await create_membership(
        session,
        project_repo,
        membership_repo,
        project,
        user_id=viewer_id,
        project_role=ProjectRole.VIEWER,
    )

    permission = await access_service.can_view_tasks(
        project_id=project.id,
        user_id=viewer_id,
        user_role=UserRole.SUPPORT_AGENT,
    )

    assert permission.allowed is True
