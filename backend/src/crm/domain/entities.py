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

    def __post_init__(self) -> None:
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

    @property
    def is_head(self) -> bool:
        """Является ли контрагент основным"""

        return self.parent_id is None

    @property
    def is_branch(self) -> bool:
        """Является ли контрагент дочерним (подчинённым основному)"""

        return self.parent_id is not None

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
