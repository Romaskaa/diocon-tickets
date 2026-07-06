from src.shared.schemas import Page, Pagination

from ..domain.entities import Ticket
from ..domain.repos import TicketFilters, TicketRepository
from ..loaders import TicketReferenceLoader
from ..mappers import map_ticket_to_view_response
from ..schemas import TicketViewResponse


class TicketQueryService:
    def __init__(
            self,
            ticket_repo: TicketRepository,
            reference_loader: TicketReferenceLoader
    ) -> None:
        self.ticket_repo = ticket_repo
        self.reference_loader = reference_loader

    async def get_tickets(
            self, pagination: Pagination, filters: TicketFilters | None = None,
    ) -> Page[TicketViewResponse]:
        page = await self.ticket_repo.paginate(pagination, filters=filters)

        relations = await self.reference_loader.load(page.items)

        def mapper(ticket: Ticket) -> TicketViewResponse:
            return map_ticket_to_view_response(
                ticket=ticket,
                reporter_full_name=relations.user_map.get(ticket.reporter_id, ""),
                assignee_full_name=relations.user_map.get(ticket.assignee_id, ""),
                counterparty_name=relations.counterparty_map.get(ticket.counterparty_id, ""),
                project_key=relations.project_map.get(ticket.project_id, ""),
            )

        return page.to_response(mapper)

    async def get_my_tickets(self) -> Page[TicketViewResponse]:
        """
        Получение списка 'моих' тикетов.
        Для клиентов - по инициатору, для поддержки - по назначению.
        """
