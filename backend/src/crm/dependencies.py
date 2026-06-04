from typing import Annotated

from fastapi import Depends

from ..shared.dependencies import SessionDep
from .domain.repo import CounterpartyRepository
from .infra.repos import SqlCounterpartyRepository
from .services import CounterpartyService


def get_counterparty_repo(session: SessionDep) -> CounterpartyRepository:
    return SqlCounterpartyRepository(session)


CounterpartyRepoDep = Annotated[CounterpartyRepository, Depends(get_counterparty_repo)]


def get_counterparty_service(
        session: SessionDep, repo: CounterpartyRepoDep
) -> CounterpartyService:
    return CounterpartyService(session, repo)


CounterpartyServiceDep = Annotated[CounterpartyService, Depends(get_counterparty_service)]
