from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.shared.schemas import Pagination
from src.tickets.domain.vo import TicketNumber
from src.tickets.services import TicketQueryService


@pytest.fixture
def ticket_view_service(fake_ticket_repo, ticket_scope_service, ticket_data_loader):
    return TicketQueryService(
        ticket_repo=fake_ticket_repo,
        ticket_scope_service=ticket_scope_service,
        reference_loader=ticket_data_loader,
    )


@pytest.mark.asyncio
class TestGetTickets:

    async def test_get_tickets_success(
            self,
            ticket_view_service,
            user_factory,
            counterparty_factory,
            ticket_factory,
    ):
        """Успешное получение тикетов с пагинацией"""

        # Подготовка данных
        counterparty_id = uuid4()
        counterparty_name = "Рога и копыта"
        reporter_id = uuid4()
        reporter_full_name = "Иванов Иван Иванович"
        assignee_full_name = "Петров Пётр Петрович"

        user = await user_factory(
            id=reporter_id,
            role=UserRole.CUSTOMER,
            counterparty_id=counterparty_id,
            full_name=reporter_full_name,
        )
        support_user = await user_factory(
            role=UserRole.SUPPORT_AGENT, full_name=assignee_full_name
        )
        await counterparty_factory(id=counterparty_id, name=counterparty_name)

        # Создание тикетов
        await ticket_factory(
            reporter_id=reporter_id,
            number=TicketNumber("TEST-26-00000001"),
            counterparty_id=counterparty_id,
        )
        await ticket_factory(
            reporter_id=reporter_id,
            number=TicketNumber("TEST-26-00000002"),
            assignee_id=support_user.id,
        )

        # Проверка результата
        page = await ticket_view_service.get_tickets(
            current_user=CurrentUser(
                user_id=reporter_id,
                email=user.email,
                role=user.role,
                counterparty_id=counterparty_id,
            ),
            pagination=Pagination(page=1, size=10),
        )

        excepted_total_items = 2

        assert page.total_items == excepted_total_items

        assert page.items[0].counterparty_name == counterparty_name
        assert page.items[0].reporter_full_name == reporter_full_name
        assert page.items[1].assignee_full_name == assignee_full_name
