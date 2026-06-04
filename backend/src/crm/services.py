from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..shared.domain.exceptions import AlreadyExistsError, NotFoundError
from .domain.entities import Counterparty
from .domain.repo import CounterpartyRepository
from .domain.vo import ContactPerson, Inn, Kpp, Okpo, Phone
from .mappers import map_counterparty_to_response
from .schemas import BranchAdd, ContactPersonIn, CounterpartyCreate, CounterpartyResponse


class CounterpartyService:
    def __init__(self, session: AsyncSession, repository: CounterpartyRepository) -> None:
        self.session = session
        self.repository = repository

    async def create(self, data: CounterpartyCreate) -> CounterpartyResponse:
        """Создание нового контрагента (по умолчанию головной)"""

        # 1. Проверка на уникальность (ИНН + email)
        exists_counterparty = await self.repository.get_by_inn(Inn(data.inn))
        if exists_counterparty is not None:
            raise AlreadyExistsError(f"Counterparty with INN {data.inn} already exists")
        exists_counterparty = await self.repository.get_by_email(data.email)
        if exists_counterparty is not None:
            raise AlreadyExistsError(f"This {data.email} email address already used")

        # 2. Создание доменных примитивов и объектов значений
        inn = Inn(data.inn)
        kpp = None if data.kpp is None else Kpp(data.kpp)
        okpo = None if data.okpo is None else Okpo(data.okpo)
        phone = Phone(data.phone)

        # 3. Формирование контактных лиц лица
        contact_persons = [
            ContactPerson.create(
                first_name=contact_person.first_name,
                last_name=contact_person.last_name,
                middle_name=contact_person.middle_name,
                phone=contact_person.phone,
                email=contact_person.email,
                messengers=contact_person.messengers,
            )
            for contact_person in data.contact_persons
        ]

        # 4. Создание доменной сущности
        counterparty = Counterparty(
            counterparty_type=data.counterparty_type,
            name=data.name,
            legal_name=data.legal_name,
            inn=inn,
            kpp=kpp,
            okpo=okpo,
            phone=phone,
            email=data.email,
            address=data.address,
            contact_persons=contact_persons,
        )

        # 5. Запись в базу данных
        await self.repository.create(counterparty)
        await self.session.commit()

        return map_counterparty_to_response(counterparty)

    async def add_branch(self, counterparty_id, data: BranchAdd) -> CounterpartyResponse:
        """
        Привязка обособленного подразделения (например другой филиал)
        """

        # 1. Проверка на существование
        exists_counterparty = await self.repository.read(counterparty_id)
        if exists_counterparty is None:
            raise NotFoundError(f"Parent counterparty with ID {counterparty_id} not found")

        # 2. Создание обособленного подразделения
        branch = exists_counterparty.create_branch(
            name=data.name,
            legal_name=data.legal_name,
            kpp=data.kpp,
            phone=data.phone,
            email=data.email,
            okpo=data.okpo,
            address=data.address,
        )

        # 3. Запись в базу данных
        await self.repository.create(branch)
        await self.session.commit()

        return map_counterparty_to_response(branch)

    async def add_contact_person(
            self, counterparty_id: UUID, data: ContactPersonIn
    ) -> CounterpartyResponse:
        """Добавление контактного лица"""

        # 1. Получение и проверка на существование контрагента
        counterparty = await self.repository.read(counterparty_id)
        if counterparty is None:
            raise NotFoundError(f"Counterparty with ID {counterparty_id} not found")

        # 2. Добавление контактного лица и обновление сущности
        counterparty.add_contact_person(
            first_name=data.first_name,
            last_name=data.last_name,
            middle_name=data.middle_name,
            phone=data.phone,
            email=data.email,
            messengers=data.messengers,
        )
        await self.repository.upsert(counterparty)
        await self.session.commit()

        return map_counterparty_to_response(counterparty)

    async def link_product(self, counterparty_id: UUID, product_id: UUID) -> None:
        """
        Привязка программного продукта к контрагенту
        (программны продукт из общего справочника)
        """

        # 1. Получение и проверка на существование контрагента
        counterparty = await self.repository.read(counterparty_id)
        if counterparty is None:
            raise NotFoundError(f"Counterparty with ID {counterparty_id} not found")

        # 2. Привязка продукта
        await self.repository.link_product(counterparty.id, product_id)
        await self.session.commit()
