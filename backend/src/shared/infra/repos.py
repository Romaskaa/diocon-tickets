import abc
from uuid import UUID

from sqlalchemy import Select, delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import Base
from ..domain.entities import Entity
from ..schemas import Page, Pagination
from ..utils.time import current_datetime


class ModelMapper[EntityT: Entity, ModelT: Base](abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def to_entity(model: ModelT) -> EntityT:
        """Преобразование ORM модели в доменную сущность"""

    @staticmethod
    @abc.abstractmethod
    def from_entity(entity: EntityT) -> ModelT:
        """Преобразование доменной сущности в ORM модель"""


class SqlAlchemyRepository[EntityT: Entity, ModelT: Base]:
    model: type[ModelT]
    model_mapper: ModelMapper[EntityT, ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity: EntityT) -> EntityT:
        model = self.model_mapper.from_entity(entity)
        self.session.add(model)
        return self.model_mapper.to_entity(model)

    async def read(self, uid: UUID) -> EntityT | None:
        stmt = select(self.model).where(self.model.id == uid)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def paginate(self, params: Pagination) -> Page[EntityT]:

        # 1. Основной запрос для получения данных
        stmt = select(self.model).order_by(self.model.created_at.desc())

        # 2. Запрос для подсчёта общего количества записей
        count_stmt = select(func.count()).select_from(stmt.subquery())

        # 3. Запрос для пагинации записей
        paginate_stmt = stmt.offset(params.offset).limit(params.size)

        # 4. Выполнение запросов
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()
        if total == 0:
            return Page.create([], total, params.page, params.size)

        results = await self.session.execute(paginate_stmt)
        models = results.scalars().all()

        # 5. Маппинг моделей БД в доменные сущности и формирование результата
        return Page.create(
            items=[self.model_mapper.to_entity(model) for model in models],
            total_items=total,
            page=params.page,
            size=params.size,
        )

    async def _paginate(self, stmt: Select, params: Pagination) -> Page[EntityT]:
        # 1. Получение общего количества
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = await self.session.scalar(count_stmt)
        if total_items == 0:
            return Page.create([], total_items, params.page, params.size)

        # 2. Получение страницы
        stmt = stmt.order_by(self.model.created_at.desc()).offset(params.offset).limit(params.size)
        results = await self.session.execute(stmt)
        models = results.scalars().all()

        return Page.create(
            items=[self.model_mapper.to_entity(model) for model in models],
            total_items=total_items,
            page=params.page,
            size=params.size,
        )

    async def update(self, uid: UUID, **kwargs) -> EntityT | None:
        stmt = (
            update(self.model)
            .values(**kwargs)
            .where(self.model.id == uid)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def upsert(self, entity: EntityT) -> None:
        model = self.model_mapper.from_entity(entity)
        await self.session.merge(model)

    async def delete(self, uid: UUID) -> None:
        stmt = delete(self.model).where(self.model.id == uid)
        await self.session.execute(stmt)

    async def exists(self, uid: UUID) -> bool:
        stmt = select(exists()).where(self.model.id == uid)
        return await self.session.scalar(stmt)

    async def get_by_ids(self, ids: list[UUID]) -> list[EntityT]:
        stmt = select(self.model).where(self.model.id.in_(ids))
        results = await self.session.execute(stmt)
        return [self.model_mapper.to_entity(model) for model in results.scalars().all()]


class InMemoryRepository[EntityT: Entity]:
    def __init__(self) -> None:
        self.data = {}

    async def create(self, entity: EntityT) -> EntityT:
        self.data[entity.id] = entity
        return entity

    async def read(self, uid: UUID) -> EntityT | None:
        return self.data.get(uid)

    async def paginate(self, params: Pagination) -> Page[EntityT]:
        items = list(self.data.values())
        return Page(
            page=params.page,
            size=params.size,
            total_items=len(items),
            total_pages=1,
            has_next=False,
            has_prev=False,
            items=items[:params.size],
        )

    async def update(self, uid: UUID, **kwargs) -> EntityT | None:
        entity = self.data.get(uid)
        if entity is None:
            return None

        for key, value in kwargs.items():
            if key in {"id", "created_at"}:
                continue
            if hasattr(entity, key):
                setattr(entity, key, value)

        entity.updated_at = current_datetime()
        self.data[uid] = entity
        return entity

    async def upsert(self, entity: EntityT) -> None:
        self.data[entity.id] = entity

    async def delete(self, uid: UUID) -> None:
        self.data.pop(uid)

    async def exists(self, uid: UUID) -> bool:
        return uid in self.data

    async def get_by_ids(self, ids: list[UUID]) -> list[EntityT]:
        return [entity for entity in self.data.values() if entity.id in ids]
