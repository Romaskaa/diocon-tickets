from collections.abc import AsyncIterable

from ..domain.entities import Entity
from ..domain.repo import Repository
from ..schemas import PageParams


async def iterate_batches(
        repository: Repository[Entity], start_page: int = 1, size: int = 50, **kwargs
) -> AsyncIterable[list[Entity]]:
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
