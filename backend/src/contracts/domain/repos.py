from ...shared.domain.repo import Repository
from .entities import ServiceContract


class ContractRepository(Repository[ServiceContract]):
    ...
