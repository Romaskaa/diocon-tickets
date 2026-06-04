import uuid

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import (
    ContactPerson,
    CounterpartyType,
    Inn,
    Kpp,
    Phone,
)
from src.iam.domain.vo import FullName
from src.shared.domain.exceptions import InvariantViolationError


@pytest.fixture
def valid_inn_legal():
    return Inn("7707083893")


@pytest.fixture
def valid_inn_ip():
    return Inn("123456789012")


@pytest.fixture
def valid_kpp():
    return Kpp("773301001")


@pytest.fixture
def valid_phone():
    return Phone("+79991234567")


@pytest.fixture
def valid_contact_person():
    return ContactPerson(
        full_name=FullName("Петрова Анна Сергеевна"),
        phone=Phone("+79991234567"),
        email="anna@example.com",
    )


# ====================== Успешное создание ======================

def test_create_legal_entity_success(valid_inn_legal, valid_kpp, valid_phone):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=valid_inn_legal,
        kpp=valid_kpp,
        phone=valid_phone,
        email="info@romashka.ru",
    )

    assert counterparty.counterparty_type == CounterpartyType.LEGAL_ENTITY
    assert counterparty.is_head is True
    assert counterparty.is_branch is False


def test_create_individual_entrepreneur_success(valid_inn_ip, valid_phone):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
        name="Иванов Иван Иванович",
        legal_name="ИП Иванов И.И.",
        inn=valid_inn_ip,
        phone=valid_phone,
        email="ivanov@example.com",
        kpp=None,
        okpo=None,
    )

    assert counterparty.counterparty_type == CounterpartyType.INDIVIDUAL_ENTREPRENEUR
    assert counterparty.is_head is True
    assert counterparty.is_branch is False


# ====================== Создание филиала через фабричный метод ======================

def test_create_branch(valid_inn_legal, valid_kpp, valid_phone):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=valid_inn_legal,
        kpp=valid_kpp,
        phone=valid_phone,
        email="info@romashka.ru",
    )

    branch = counterparty.create_branch(
        name="Филиал в Санкт-Петербурге",
        legal_name="ООО Ромашка (филиал в СПб)",
        kpp="784201001",
        phone="+78121234567",
        email="spb@romashka.ru",
        address="г. Санкт-Петербург, Невский пр., 1",
    )

    assert branch.counterparty_type == CounterpartyType.BRANCH
    assert branch.parent_id == counterparty.id
    assert branch.inn == counterparty.inn
    assert branch.is_head is False
    assert branch.is_branch is True
    assert branch.kpp.value == "784201001"


def test_create_branch_invalid_counterparty_type(valid_inn_ip, valid_phone):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
        name="ИП Иванов",
        legal_name="ИП Иванов И.И.",
        inn=valid_inn_ip,
        phone=valid_phone,
        email="ip@example.com",
    )

    with pytest.raises(
            InvariantViolationError, match="impossible to assign a branch to a non-legal entity"
    ):
        counterparty.create_branch(
            name="Филиал",
            legal_name="Филиал ИП",
            kpp="123456789",
            phone="+79991234567",
            email="branch@ip.ru",
        )


# ====================== Ошибки инвариантов при прямом создании ======================

def test_legal_entity_without_kpp_raises_error(valid_inn_legal, valid_phone):
    with pytest.raises(InvariantViolationError, match="KPP required"):
        Counterparty(
            counterparty_type=CounterpartyType.LEGAL_ENTITY,
            name="ООО Ромашка",
            legal_name="Общество с ограниченной ответственностью «Ромашка»",
            inn=valid_inn_legal,
            kpp=None,
            phone=valid_phone,
            email="info@romashka.ru",
        )


def test_ip_with_kpp_raises_error(valid_inn_ip, valid_kpp, valid_phone):
    with pytest.raises(InvariantViolationError, match="KPP not required"):
        Counterparty(
            counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
            name="ИП Иванов",
            legal_name="ИП Иванов И.И.",
            inn=valid_inn_ip,
            kpp=valid_kpp,
            phone=valid_phone,
            email="ip@example.com",
        )


def test_wrong_inn_length_for_legal_entity(valid_inn_ip, valid_kpp, valid_phone):
    with pytest.raises(InvariantViolationError, match="10 digits"):
        Counterparty(
            counterparty_type=CounterpartyType.LEGAL_ENTITY,
            name="ООО Ромашка",
            legal_name="Общество с ограниченной ответственностью «Ромашка»",
            inn=valid_inn_ip,
            kpp=valid_kpp,
            phone=valid_phone,
            email="info@romashka.ru",
        )


def test_wrong_inn_length_for_ip(valid_inn_legal, valid_phone):
    with pytest.raises(InvariantViolationError, match="12 digits"):
        Counterparty(
            counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
            name="ИП Иванов",
            legal_name="ИП Иванов И.И.",
            inn=valid_inn_legal,
            phone=valid_phone,
            email="ip@example.com",
        )


def test_branch_without_parent_id_raises_error(valid_inn_legal, valid_kpp, valid_phone):
    with pytest.raises(InvariantViolationError, match="specify the ID of the head counterparty"):
        Counterparty(
            counterparty_type=CounterpartyType.BRANCH,
            name="Филиал",
            legal_name="Филиал в СПб",
            inn=valid_inn_legal,
            kpp=valid_kpp,
            phone=valid_phone,
            email="branch@example.com",
            parent_id=None,  # явно None
        )


# ====================== Свойства ======================

def test_is_head_and_is_branch_properties():
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="Головная компания",
        legal_name="Головная компания",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        phone=Phone("+79991234567"),
        email="head@company.ru",
    )

    assert counterparty.is_head is True
    assert counterparty.is_branch is False

    branch = Counterparty(
        counterparty_type=CounterpartyType.BRANCH,
        name="Филиал",
        legal_name="Филиал",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        phone=Phone("+79991234567"),
        email="branch@company.ru",
        parent_id=uuid.uuid4(),
    )

    assert branch.is_head is False
    assert branch.is_branch is True


def test_add_contact_person_success():
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="Головная компания",
        legal_name="Головная компания",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        phone=Phone("+79991234567"),
        email="head@company.ru",
    )
    counterparty.add_contact_person(
        first_name="Иван",
        last_name="Иванов",
        middle_name="Иванович",
        phone="88005553535",
        email="ivanov.ivan@mail.ru",
        messengers={"vk": "12345"}
    )

    assert counterparty.contact_persons != []
    assert counterparty.contact_persons[0].full_name.value == "Иванов Иван Иванович"
    assert counterparty.updated_at > counterparty.created_at
