from collections.abc import AsyncIterable

from ..domain.entities import Entity
from ..domain.repo import Repository
from ..schemas import PageParams


async def iterate_batches[EntityT: Entity](
        repository: Repository[EntityT], start_page: int = 1, size: int = 50, **kwargs
) -> AsyncIterable[list[EntityT]]:
    """
    Итератор по коллекции сущностей (реализация паттерна batching)
    """

    page = start_page
    batch = await repository.paginate(PageParams(page=page, size=size), **kwargs)

    yield batch.items

    while batch.has_next:
        page += 1
        batch = await repository.paginate(PageParams(page=page, size=size), **kwargs)
        yield batch.items
