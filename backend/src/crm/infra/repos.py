from uuid import UUID

from sqlalchemy import func, select

from ...iam.domain.entities import User
from ...iam.domain.vo import FullName
from ...products.domain.entities import SoftwareProduct
from ...products.infra.models import SoftwareProductOrm
from ...products.infra.repo import SoftwareProductMapper
from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ...shared.schemas import Page, PageParams
from ..domain.entities import Counterparty
from ..domain.vo import ContactPerson, Inn, Kpp, Okpo, Phone
from .models import CounterpartyOrm, CounterpartyProductOrm


class CounterpartyMapper(ModelMapper[Counterparty, CounterpartyOrm]):

    @staticmethod
    def to_entity(model: CounterpartyOrm) -> Counterparty:
        return Counterparty(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            counterparty_type=model.counterparty_type,
            name=model.name,
            legal_name=model.legal_name,
            inn=Inn(model.inn),
            kpp=None if model.kpp is None else Kpp(model.kpp),
            okpo=None if model.okpo is None else Okpo(model.okpo),
            phone=None if model.phone is None else Phone(model.phone),
            email=model.email,
            address=model.address,
            avatar_url=model.avatar_url,
            contact_persons=[
                ContactPerson(
                    full_name=FullName(contact_person["full_name"]),
                    phone=Phone(contact_person["phone"]),
                    email=contact_person["email"],
                    messengers=contact_person["messengers"],
                )
                for contact_person in model.contact_persons
            ],
            is_active=model.is_active,
            parent_id=model.parent_id,
        )

    @staticmethod
    def from_entity(entity: Counterparty) -> CounterpartyOrm:
        return CounterpartyOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            counterparty_type=entity.counterparty_type,
            name=entity.name,
            legal_name=entity.legal_name,
            inn=entity.inn.value,
            kpp=None if entity.kpp is None else entity.kpp.value,
            okpo=None if entity.okpo is None else entity.okpo.value,
            phone=entity.phone.value,
            email=entity.email,
            address=entity.address,
            avatar_url=entity.avatar_url,
            contact_persons=[
                {
                    "full_name": contact_person.full_name.value,
                    "phone": contact_person.phone.value,
                    "email": contact_person.email,
                    "messengers": contact_person.messengers,
                }
                for contact_person in entity.contact_persons
            ],
            is_active=entity.is_active,
            parent_id=entity.parent_id,
        )


class SqlCounterpartyRepository(SqlAlchemyRepository[Counterparty, CounterpartyOrm]):
    model = CounterpartyOrm
    model_mapper = CounterpartyMapper

    async def get_by_email(self, email: str) -> Counterparty | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.email == email) &
                (self.model.parent_id is None)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_by_inn(self, inn: Inn) -> Counterparty | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.inn == inn.value) &
                (self.model.parent_id is None)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_with_descendants(self, counterparty_id: UUID) -> list[Counterparty]:
        # 1. Запрос для выбора корневого элемента
        recursive_cte = (
            select(self.model)
            .where(self.model.id == counterparty_id)
            .cte(name="counterparty_tree", recursive=True)
        )

        # 2. Рекурсивная часть: присоединение детей и найденных родителей
        recursive_cte = recursive_cte.union_all(
            select(self.model).join(recursive_cte, self.model.id == recursive_cte.c.id)
        )

        # 3. Финальный запрос из CTE
        stmt = select(self.model).from_statement(select(recursive_cte))

        # 4. Выполнение запроса и преобразование результата
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [self.model_mapper.to_entity(model) for model in models]

    async def get_customers(self, counterparty_id: UUID, params: PageParams) -> Page[User]:
        from ...iam.infra.models import UserOrm
        from ...iam.infra.repos import UserMapper

        # 1. Основной запрос
        stmt = select(UserOrm).where(UserOrm.counterparty_id == counterparty_id)

        # 2. Получение количества клиентов
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        if total == 0:
            return Page.create([], total, params.page, params.size)

        # 3. Получение списка клиентов
        stmt = stmt.offset(params.offset).limit(params.size)
        results = await self.session.execute(stmt)
        models = results.scalars().all()

        # 4. Расчёт результата
        items = [UserMapper.to_entity(model) for model in models]
        return Page.create(items, total, params.page, params.size)

    async def link_product(self, counterparty_id: UUID, product_id: UUID) -> None:
        self.session.add(
            CounterpartyProductOrm(counterparty_id=counterparty_id, product_id=product_id)
        )

    async def get_products(
            self, counterparty_id: UUID, pagination: PageParams,
    ) -> Page[SoftwareProduct]:
        # 1. Базовый запрос на получение программный продуктов
        stmt = (
            select(SoftwareProductOrm)
            .join(
                CounterpartyProductOrm,
                SoftwareProductOrm.id == CounterpartyProductOrm.product_id,
            )
            .where(CounterpartyProductOrm.counterparty_id == counterparty_id)
            .distinct()  # 1.1 Исключение дубликатов из-за разных environment
        )

        # 2. Подсчёт общего количества записей удовлетворяющих запросу
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = await self.session.scalar(count_stmt)
        if total_items == 0:
            return Page.create([], total_items, pagination.page, pagination.size)

        # 3. Пагинация программных продуктов
        stmt = stmt.offset(pagination.offset).limit(pagination.size)
        results = await self.session.execute(stmt)
        models = results.scalars().all()

        # 4. Преобразование ORM моделей в доменные сущности
        items = [SoftwareProductMapper.to_entity(model) for model in models]

        return Page.create(items, total_items, pagination.page, pagination.size)
