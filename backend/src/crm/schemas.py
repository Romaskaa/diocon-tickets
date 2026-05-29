from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from .domain.vo import CounterpartyType, Inn


class ContactPersonIn(BaseModel):
    """Добавление контактного лица контрагента"""

    first_name: str = Field(..., description="Имя")
    last_name: str = Field(..., description="Фамилия")
    middle_name: str | None = Field(None, description="Отчество")
    phone: str = Field(..., description="Номер телефона", examples=["88005553535", "+78005553535"])
    email: EmailStr = Field(..., description="Адрес электронной почты")
    messengers: dict[str, str] = Field(
        default_factory=dict,
        description="Контакты в мессенджерах",
        examples=[{"telegram": "exampleUser05", "vk": "1254752"}]
    )


class ContactPersonOut(BaseModel):
    """Созданное контактное лицо"""

    full_name: str = Field(..., description="ФИО лица", examples=["Иванов Иван Иванович"])
    phone: str = Field(..., description="Номер телефона", examples=["88005553535", "+78005553535"])
    email: EmailStr = Field(..., description="Адрес электронной почты")
    messengers: dict[str, str] = Field(
        default_factory=dict,
        description="Контакты в мессенджерах",
        examples=[{"telegram": "exampleUser05", "vk": "1254752"}],
    )


class CounterpartyBase(BaseModel):
    """Базовая API схема контрагента"""

    name: str = Field(..., max_length=255, description="Наименование")
    legal_name: str = Field(..., max_length=255, description="Юридическое наименование")
    kpp: str = Field(..., max_length=11, description="КПП - код причины постановки на учёт")
    okpo: str | None = Field(
        None,
        max_length=10,
        description="ОКПО — Общероссийский классификатор предприятий и организаций",
    )
    phone: str = Field(..., description="Номер телефона", examples=["88005553535", "+78005553535"])
    email: EmailStr = Field(..., description="Адрес электронной почты")
    address: str | None = Field(None, description="Фактический адрес компании")


class CounterpartyCreate(CounterpartyBase):
    """Создание контрагента (создаётся основной контрагент (master), без вложенности)"""

    counterparty_type: CounterpartyType = Field(..., description="Тип контрагента")
    inn: str = Field(..., max_length=12, description="ИНН контрагента")
    contact_persons: list[ContactPersonIn] = Field(
        default_factory=list, description="Контактные лица контрагента"
    )


class BranchAdd(CounterpartyBase):
    """Добавление обособленного подразделения
    (контактное лицо можно добавить через обновление контрагента).
    """


class CounterpartyEdit(BaseModel):
    """
    Редактирование информации о контрагенте
    """

    name: str | None = Field(None, max_length=255, description="Наименование")
    legal_name: str | None = Field(None, max_length=255, description="Юридическое наименование")
    okpo: str | None = Field(
        None,
        max_length=10,
        description="ОКПО — Общероссийский классификатор предприятий и организаций",
    )
    phone: str | None = Field(
        None, description="Номер телефона", examples=["88005553535", "+78005553535"]
    )
    email: EmailStr | None = Field(None, description="Адрес электронной почты")
    address: str | None = Field(None, description="Фактический адрес компании")


class CounterpartyResponse(CounterpartyBase):
    """API ответ для получения контрагента"""

    id: UUID = Field(..., description="ID созданного контрагента")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    counterparty_type: CounterpartyType = Field(..., description="Тип контрагента")
    inn: str = Field(..., description="ИНН контрагента")
    avatar_url: str | None = Field(None, description="URL адрес аватарки")
    contact_persons: list[ContactPersonOut] = Field(
        default_factory=list, description="Контактные лица"
    )
    parent_id: UUID | None = Field(None, description="ID головного контрагента")
    is_active: bool = Field(True, description="Доступен ли контрагент в системе")
    is_head: bool = Field(True, description="Является ли контрагент головным")
    is_branch: bool = Field(False, description="Является ли дочерним объектом")


@dataclass(frozen=True)
class CounterpartyFilters:
    """
    Фильтры для поиска контрагентов
    """

    query: str | None = None
    email: str | None = None
    inn: Inn | None = None
