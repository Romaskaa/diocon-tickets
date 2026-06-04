from typing import ClassVar, Self

import re
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import EmailStr

from ...iam.domain.vo import FullName
from ...shared.domain.vo import ValueObject


class CounterpartyType(StrEnum):
    """Типы контрагентов"""

    INDIVIDUAL = "Физическое лицо"
    INDIVIDUAL_ENTREPRENEUR = "Индивидуальный предприниматель"
    LEGAL_ENTITY = "Юридическое лицо"
    FOREIGN_LEGAL_ENTITY = "Иностранное юридическое лицо"
    BRANCH = "Обособленное подразделение"


@dataclass(frozen=True, slots=True)
class Inn(ValueObject):
    """
    ИНН — Идентификационный номер налогоплательщика (10 или 12 цифр)
    """

    LENGTHS: ClassVar[tuple[int, ...]] = (10, 12)

    value: str = field(compare=True, hash=True, repr=False)

    def __post_init__(self) -> None:
        cleaned = self.value.strip().replace(" ", "").replace("-", "")

        if not cleaned.isdigit():
            raise ValueError("INN can contains only digits")

        if len(cleaned) not in self.LENGTHS:
            raise ValueError(f"INN must contain 10 or 12 digits (received {len(cleaned)})")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        v = self.value
        if len(v) == self.LENGTHS[0]:
            return f"{v[:4]} {v[4:]}"
        return f"{v[:4]} {v[4:8]} {v[8:]}"

    def __repr__(self) -> str:
        return f"Inn({self.value!r})"

    @property
    def is_legal_entity(self) -> bool:
        """Является ли юридическим лицом"""

        return len(self.value) == self.LENGTHS[0]

    @property
    def is_individual(self) -> bool:
        """Является ли индивидуальным предпринимателем"""

        return len(self.value) == self.LENGTHS[1]


@dataclass(frozen=True, slots=True)
class Kpp(ValueObject):
    """
    КПП — Код причины постановки на учёт (9 цифр)
    """

    LENGTH: ClassVar[int] = 9

    value: str = field(compare=True, hash=True, repr=False)

    def __post_init__(self) -> None:
        cleaned = self.value.strip().replace(" ", "").replace("-", "")

        if not cleaned.isdigit():
            raise ValueError("KPP must contains only digits")

        if len(cleaned) != self.LENGTH:
            raise ValueError(f"KPP must contain exactly 9 digits (received {len(cleaned)})")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        v = self.value
        return f"{v[:4]}/{v[4:6]}/{v[6:]}"

    def __repr__(self) -> str:
        return f"Kpp({self.value!r})"


@dataclass(frozen=True, slots=True)
class Okpo(ValueObject):
    """
    ОКПО — Общероссийский классификатор предприятий и организаций
    (8 цифр — юридического лица, 10 цифр — ИП и обособленные подразделения)
    """

    LENGTHS: ClassVar[tuple[int, ...]] = (8, 10)

    value: str = field(compare=True, hash=True, repr=False)

    def __post_init__(self) -> None:
        cleaned = self.value.strip().replace(" ", "").replace("-", "")

        if not cleaned.isdigit():
            raise ValueError("OKPO must contains only digits")

        if len(cleaned) not in self.LENGTHS:
            raise ValueError(f"OKPO must contains 8 or 10 digits (received {len(cleaned)})")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Okpo({self.value!r})"

    @property
    def is_legal_entity(self) -> bool:
        """Принадлежит ли юридическому лицу"""

        return len(self.value) == self.LENGTHS[0]

    @property
    def is_individual_or_branch(self) -> bool:
        """Является ИП или обособленным подразделением"""

        return len(self.value) == self.LENGTHS[1]


@dataclass(frozen=True, slots=True)
class Phone:
    """
    Номер телефона (российский формат, приводится к формату к +7(XXX)XXX-XX-XX)
    """

    value: str = field(compare=True, hash=True, repr=False)

    # Российские мобильные и городские номера
    PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^\+?7\d{10}$|^8\d{10}$|^9\d{9}$|^7\d{10}$"
    )
    # Длина после нормализации (+7 + 10 символов)
    NORMALIZED_LENGTH: ClassVar[int] = 12
    # Возможные длины
    LENGTHS: ClassVar[tuple[int, ...]] = (10, 11)

    def __post_init__(self) -> None:
        digits = "".join(c for c in self.value if c.isdigit())
        if not digits:
            raise ValueError("Phone number cannot be empty")

        if digits.startswith("8"):
            normalized = "+7" + digits[1:]
        elif digits.startswith(("7", "9")):
            if len(digits) == self.LENGTHS[0]:
                normalized = "+7" + digits
            elif len(digits) == self.LENGTHS[1]:
                normalized = "+7" + digits[1:]
            else:
                normalized = "+7" + digits
        else:
            normalized = "+7" + digits

        if not self.PATTERN.match(normalized):
            raise ValueError(
                "Invalid phone number. "
                "Excepted russian number: +7XXXXXXXXXX or 8XXXXXXXXXX"
            )

        if len(normalized) != self.NORMALIZED_LENGTH:
            raise ValueError(
                f"Phone number must contains 10 digits after +7 (received {len(digits)})"
            )

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return f"+7 ({self.value[2:5]}) {self.value[5:8]}-{self.value[8:10]}-{self.value[10:12]}"

    def __repr__(self) -> str:
        return f"Phone({self.value!r})"


@dataclass(frozen=True, slots=True)
class ContactPerson(ValueObject):
    """
    Контактное лицо контрагента (физическое лицо)
    """

    AVAILABLE_MESSENGERS: ClassVar[frozenset[str]] = frozenset({
        "telegram", "whatsapp", "vk", "max", "signal", "skype",
    })

    full_name: FullName
    phone: Phone
    email: EmailStr
    messengers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        disabled = set(self.messengers) - self.AVAILABLE_MESSENGERS
        if disabled:
            raise ValueError(
                f"Disabled messengers: {', '.join(disabled)}. "
                f"Available: {', '.join(sorted(self.AVAILABLE_MESSENGERS))}"
            )

        for key, value in self.messengers.items():
            if not value or not isinstance(value, str):
                raise ValueError(f"Value for {key} must be non empty string")

    def __repr__(self) -> str:
        return (
            f"ContactPerson("
            f"full_name={self.full_name!r}, "
            f"phone={self.phone!r}, "
            f"email={self.email!r}, "
            f"messengers={self.messengers!r})"
        )

    @classmethod
    def create(
            cls,
            first_name: str,
            last_name: str,
            middle_name: str | None,
            phone: str,
            email: str,
            messengers: dict[str, str],
    ) -> Self:
        return cls(
            full_name=FullName(
                f"{last_name} {first_name} {middle_name if middle_name is not None else ''}"
            ),
            phone=Phone(phone),
            email=email,
            messengers=messengers,
        )
