import pytest

from src.iam.domain.vo import UserRole
from src.tickets.domain.vo import TicketNumber
from src.tickets.loaders import TicketRelations


@pytest.fixture
async def ticket_list(counterparty_factory, user_factory, project_factory, ticket_factory):

    # Создание контрагента
    counterparty = await counterparty_factory()
    # Создание клиента и сотрудника поддержки
    customer = await user_factory(role=UserRole.CUSTOMER, counterparty_id=counterparty.id)
    support_agent = await user_factory(role=UserRole.SUPPORT_AGENT)
    # Создание проекта
    project = await project_factory()

    return [
        await ticket_factory(
            number=TicketNumber("TEST-26-00000001"),
            reporter_id=customer.id,
            created_by=customer.id,
            created_by_role=customer.role,
            counterparty_id=counterparty.id,
        ),
        await ticket_factory(
            ticket_number=TicketNumber("TEST-26-00000002"),
            title="Test",
            description="Test description",
            reporter_id=customer.id,
            created_by=support_agent.id,
            created_by_role=support_agent.role,
            counterparty_id=counterparty.id,
        ),
        await ticket_factory(
            number=TicketNumber("TEST-26-00000003"),
            reporter_id=customer.id,
            created_by=support_agent.id,
            created_by_role=support_agent.role,
            counterparty_id=counterparty.id,
            project_id=project.id,
            assignee_id=support_agent.id,
        ),
    ]


@pytest.mark.asyncio
class TestTicketDataLoader:

    async def test_load_populates_relations_correctly(self, ticket_data_loader, ticket_list):
        """Успешная загрузка и заполнение маппингов"""

        reporter_ids = {ticket.reporter_id for ticket in ticket_list}
        assignee_ids = {
            ticket.assignee_id for ticket in ticket_list if ticket.assignee_id is not None
        }
        user_ids = reporter_ids | assignee_ids

        counterparty_ids = {
            ticket.counterparty_id for ticket in ticket_list if ticket.counterparty_id is not None
        }
        project_ids = {
            ticket.project_id for ticket in ticket_list if ticket.project_id is not None
        }

        relations = await ticket_data_loader.load(ticket_list)

        for user_id in user_ids:
            assert user_id in relations.user_map
            assert isinstance(relations.user_map[user_id], str)

        for counterparty_id in counterparty_ids:
            assert counterparty_id in relations.counterparty_map
            assert isinstance(relations.counterparty_map[counterparty_id], str)

        for project_id in project_ids:
            assert project_id in relations.project_map
            assert isinstance(relations.project_map[project_id], str)

    async def test_load_empty_ticket_list(self, ticket_data_loader):
        """Проверка обработки пустого списка тикетов"""

        relations = await ticket_data_loader.load([])
        assert relations == TicketRelations(user_map={}, counterparty_map={}, project_map={})
