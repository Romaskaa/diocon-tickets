from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.schemas import CurrentUser
from ...shared.schemas import Page, Pagination
from ..domain.entities import Ticket
from ..domain.repos import TicketFilters, TicketRepository
from ..domain.services import TicketScopeService
from ..loaders import TicketDataLoader
from ..mappers import map_ticket_to_view_response
from ..schemas import TicketViewResponse


class TicketViewService:
    def __init__(
            self,
            ticket_repo: TicketRepository,
            ticket_scope_service: TicketScopeService,
            ticket_data_loader: TicketDataLoader
    ) -> None:
        self.ticket_repo = ticket_repo
        self.ticket_scope_service = ticket_scope_service
        self.ticket_data_loader = ticket_data_loader

    async def get_tickets(
            self,
            current_user: CurrentUser,
            pagination: Pagination,
            filters: TicketFilters | None = None,
    ) -> Page[TicketViewResponse]:
        """Получение списка тикетов с пагинацией"""

        # 1. Определение области видимости
        scopes = await self.ticket_scope_service.get_scopes(
            user_id=current_user.user_id,
            user_role=current_user.role,
            user_counterparty_id=current_user.counterparty_id,
        )
        if scopes is None:
            raise PermissionDeniedError(
                f"User {current_user.user_id} with role {current_user.role} "
                f"does not have permission to view any tickets."
            )

        # 2. Получение страницы с тикетами с учётом области видимости и фильтров
        page = await self.ticket_repo.paginate(pagination, scopes=scopes, filters=filters)

        # 3. Пакетная загрузка дополнительной информации для тикета
        relations = await self.ticket_data_loader.load(page.items)

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
