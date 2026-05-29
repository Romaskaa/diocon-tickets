from typing import Self

from dataclasses import dataclass, field
from uuid import UUID

from pydantic import EmailStr

from ...shared.domain.entities import Entity
from ...shared.domain.exceptions import InvariantViolationError
from ...shared.utils.time import current_datetime
from .vo import ContactPerson, CounterpartyType, Inn, Kpp, Okpo, Phone

INDIVIDUAL_INN_LENGTH = 12
LEGAL_INN_LENGTH = 10


@dataclass(kw_only=True)
class Counterparty(Entity):
    """
    Контрагент - компания с которой ведётся работа (заказчик)
    """

    counterparty_type: CounterpartyType
    name: str
    legal_name: str
    inn: Inn
    kpp: Kpp | None = None
    okpo: Okpo | None = None
    phone: Phone
    email: EmailStr
    address: str | None = None
    avatar_url: str | None = None
    contact_persons: list[ContactPerson] = field(default_factory=list)
    is_active: bool = True

    # Поля для master-slave иерархии (удобно для филиалов)
    parent_id: UUID | None = None

    def __post_init__(self) -> None:  # noqa: C901
        """Проверка инвариантов контрагента"""

        # 1. Проверка корректности длины ИНН в зависимости от типа контрагента
        inn_length = len(self.inn.value)
        match self.counterparty_type:
            case CounterpartyType.INDIVIDUAL | CounterpartyType.INDIVIDUAL_ENTREPRENEUR:
                if inn_length != INDIVIDUAL_INN_LENGTH:
                    raise InvariantViolationError(
                        "For an individual, the IIN must contain 12 digits "
                        f"(received {inn_length})"
                    )
            case CounterpartyType.LEGAL_ENTITY | CounterpartyType.BRANCH:
                if inn_length != LEGAL_INN_LENGTH:
                    raise InvariantViolationError(
                        "For a legal entity, the IIN must contain 10 digits "
                        f"(received {inn_length})"
                    )

        # 3. Проверка наличия КПП
        if self.counterparty_type in {CounterpartyType.LEGAL_ENTITY, CounterpartyType.BRANCH}:
            if self.kpp is None:
                raise InvariantViolationError(
                    f"For counterparty type '{self.counterparty_type.value}' KPP required"
                )
        elif self.kpp is not None:
            raise InvariantViolationError(
                f"For counterparty type {self.counterparty_type.value} KPP not required"
            )

        # 4. Обособленное подразделение должно быть привязано к основному контрагенту
        if self.counterparty_type == CounterpartyType.BRANCH and self.parent_id is None:
            raise InvariantViolationError(
                "It is necessary to specify the ID of the head counterparty "
                "to attach a branch. Missing parent_id value."
            )

        # 5. Телефон и электронная почат контактного лица должны быть уникальны
        seen_contact_data = set()
        for contact_person in self.contact_persons:
            contact_data = (contact_person.phone, contact_person.email)
            if contact_data in seen_contact_data:
                raise InvariantViolationError(
                    "Combination of phone number and email must be unique for contact persons"
                )

            seen_contact_data.add(contact_data)

    @property
    def is_head(self) -> bool:
        """Является ли контрагент основным"""

        return self.parent_id is None

    @property
    def is_branch(self) -> bool:
        """Является ли контрагент дочерним (подчинённым основному)"""

        return self.parent_id is not None

    def edit(
            self,
            *,
            name: str | None = None,
            legal_name: str | None = None,
            okpo: Okpo | None = None,
            phone: Phone | None = None,
            email: EmailStr | None = None,
            address: str | None = None,
    ) -> None:
        """
        Редактирование основных данных контрагента.
        Нельзя изменить тип, ИНН, КПП или parent_id.
        """

        is_edited = False

        if name is not None and name.strip() and name.strip() != self.name:
            self.name = name.strip()
            is_edited = True

        if legal_name is not None and legal_name.strip() and legal_name.strip() != self.name:
            self.legal_name = legal_name.strip()
            is_edited = True

        if okpo is not None and okpo != self.okpo:
            self.okpo = okpo
            is_edited = True

        if phone is not None and phone != self.phone:
            self.phone = phone
            is_edited = True

        if email is not None and email != self.email:
            self.email = email
            is_edited = True

        if address is not None and address.strip() and address.strip() != self.address:
            self.address = address.strip()
            is_edited = True

        if is_edited:
            self.updated_at = current_datetime()

    def create_branch(
            self,
            name: str,
            legal_name: str,
            kpp: str,
            phone: str,
            email: EmailStr,
            okpo: str | None = None,
            address: str | None = None,
    ) -> "Counterparty":
        """Создание обособленного подразделения с привязкой к контрагенту"""

        if self.counterparty_type != CounterpartyType.LEGAL_ENTITY:
            raise InvariantViolationError(
                "It is impossible to assign a branch to a non-legal entity"
            )

        return Counterparty(
            counterparty_type=CounterpartyType.BRANCH,
            name=name,
            legal_name=legal_name,
            inn=self.inn,
            kpp=Kpp(kpp),
            okpo=None if okpo is None else Okpo(okpo),
            phone=Phone(phone),
            email=email,
            address=address,
            parent_id=self.id
        )

    def add_contact_person(
            self,
            first_name: str,
            last_name: str,
            phone: str,
            email: str,
            middle_name: str | None = None,
            messengers: dict[str, str] | None = None,
    ) -> Self:
        """Добавления контактного лица"""

        # Проверка, нет ли такого же телефона и email у добавленных контактных лиц
        for contact_person in self.contact_persons:
            if contact_person.phone == Phone(phone) and contact_person.email == email:
                raise ValueError(
                    f"Contact person with phone - '{phone}' and email - '{email}' already exists"
                )

        self.contact_persons.append(
            ContactPerson.create(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                phone=phone,
                email=email,
                messengers=messengers,
            )
        )
        self.updated_at = current_datetime()

    def remove_contact_person(self, phone: Phone, email: str) -> None:
        """Удаление контактного лица"""

        target = None

        for i, contact_person in enumerate(self.contact_persons):
            if contact_person.phone == phone and contact_person.email == email:
                target = i
                break

        if target is not None:
            self.contact_persons.pop(target)
            self.updated_at = current_datetime()
