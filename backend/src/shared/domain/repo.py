from typing import Protocol

from uuid import UUID

from ..schemas import Page, PageParams
from .entities import Entity


class Repository[EntityT: Entity](Protocol):

    async def create(self, entity: EntityT) -> EntityT: ...

    async def read(self, uid: UUID) -> EntityT | None: ...

    async def paginate(self, params: PageParams) -> Page[EntityT]: ...

    async def update(self, uid: UUID, **kwargs) -> EntityT: ...

    async def upsert(self, entity: EntityT) -> None: ...

    async def delete(self, uid: UUID) -> None: ...
