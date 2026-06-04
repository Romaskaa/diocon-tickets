from sqlalchemy.ext.asyncio import AsyncSession

from .domain.repos import ContractRepository


class ContractService:
    def __init__(self, session: AsyncSession, repository: ContractRepository) -> None:
        self.session = session
        self.repository = repository

    async def create(self): ...
