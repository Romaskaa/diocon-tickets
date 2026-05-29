from typing import Annotated

from fastapi import Depends, Query
from pydantic import EmailStr

from ..shared.dependencies import SessionDep
from .domain.repo import CounterpartyRepository
from .domain.vo import Inn
from .infra.repos import SqlCounterpartyRepository
from .schemas import CounterpartyFilters
from .services import CounterpartyService


def get_counterparty_repo(session: SessionDep) -> SqlCounterpartyRepository:
    return SqlCounterpartyRepository(session)


CounterpartyRepoDep = Annotated[CounterpartyRepository, Depends(get_counterparty_repo)]


def get_counterparty_service(
        session: SessionDep, repo: CounterpartyRepoDep
) -> CounterpartyService:
    return CounterpartyService(session, repo)


CounterpartyServiceDep = Annotated[CounterpartyService, Depends(get_counterparty_service)]


def get_counterparty_filters(
        query: Annotated[
            str | None, Query(..., description="Поисковый запрос (наименования, инн)")
        ] = None,
        email: Annotated[
            EmailStr | None, Query(..., description="Email контрагента")
        ] = None,
        inn: Annotated[str | None, Query(..., description="ИНН контрагента")] = None,
) -> CounterpartyFilters:
    return CounterpartyFilters(query=query, email=email, inn=Inn(inn))


CounterpartyFiltersDep = Annotated[CounterpartyFilters, Depends(get_counterparty_filters)]
