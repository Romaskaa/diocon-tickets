import uuid

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import ContactPerson, CounterpartyType, Inn, Kpp, Okpo, Phone
from src.crm.infra.models import CounterpartyOrm
from src.crm.infra.repos import CounterpartyMapper
from src.iam.domain.vo import FullName
from src.shared.utils.time import current_datetime


@pytest.fixture
def sample_uuid():
    return uuid.uuid4()


@pytest.fixture
def sample_datetime():
    return current_datetime()


@pytest.fixture
def sample_counterparty_model(sample_uuid, sample_datetime):
    return CounterpartyOrm(
        id=sample_uuid,
        created_at=sample_datetime,
        updated_at=sample_datetime,
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn="7707083893",
        kpp="773301001",
        okpo="00123456",
        phone="+79991234567",
        email="info@romashka.ru",
        address="г. Москва, ул. Ленина, д. 10",
        avatar_url="https://example.com/logo.png",
        contact_persons=[{
            "full_name": "Петрова Анна Сергеевна",
            "phone": "+79991234567",
            "email": "anna.petrovna@romashka.ru",
            "messengers": {"telegram": "@anna_p", "whatsapp": "+79991234567"}
        }],
        is_active=True,
    )


@pytest.fixture
def sample_counterparty_entity(sample_uuid, sample_datetime):
    return Counterparty(
        id=sample_uuid,
        created_at=sample_datetime,
        updated_at=sample_datetime,
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        okpo=Okpo("00123456"),
        phone=Phone("+79991234567"),
        email="info@romashka.ru",
        address="г. Москва, ул. Ленина, д. 10",
        avatar_url="https://example.com/logo.png",
        contact_persons=[ContactPerson(
            full_name=FullName("Петрова Анна Сергеевна"),
            phone=Phone("+79991234567"),
            email="anna.petrovna@romashka.ru",
            messengers={"telegram": "@anna_p", "whatsapp": "+79991234567"}
        )],
        is_active=True,
    )


def test_to_entity_full_mapping(sample_counterparty_model):
    """Проверка полного преобразование из ORM в доменную сущность"""

    entity = CounterpartyMapper.to_entity(sample_counterparty_model)

    assert entity.id == sample_counterparty_model.id
    assert entity.created_at == sample_counterparty_model.created_at
    assert entity.updated_at == sample_counterparty_model.updated_at
    assert entity.counterparty_type == sample_counterparty_model.counterparty_type
    assert entity.name == sample_counterparty_model.name
    assert entity.legal_name == sample_counterparty_model.legal_name
    assert entity.inn.value == sample_counterparty_model.inn
    assert entity.kpp.value == sample_counterparty_model.kpp
    assert entity.okpo.value == sample_counterparty_model.okpo
    assert entity.phone.value == sample_counterparty_model.phone
    assert entity.email == sample_counterparty_model.email
    assert entity.address == sample_counterparty_model.address
    assert entity.avatar_url == sample_counterparty_model.avatar_url
    assert entity.is_active == sample_counterparty_model.is_active

    # Проверка контактного лица
    assert entity.contact_persons
    assert entity.contact_persons[0].full_name == "Петрова Анна Сергеевна"
    assert entity.contact_persons[0].phone.value == (
        sample_counterparty_model.contact_persons[0]["phone"]
    )
    assert entity.contact_persons[0].email == (
        sample_counterparty_model.contact_persons[0]["email"]
    )
    assert entity.contact_persons[0].messengers == \
           sample_counterparty_model.contact_persons[0]["messengers"]


def test_to_entity_null_fields(sample_uuid, sample_datetime):

    model = CounterpartyOrm(
        id=sample_uuid,
        created_at=sample_datetime,
        updated_at=sample_datetime,
        counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
        name="Иванов Иван Иванович",
        legal_name="Иванов И.И. (ИП)",
        inn="500100732259",
        kpp=None,
        okpo=None,
        phone="+79991234567",
        email="ivanov@example.com",
        address=None,
        avatar_url=None,
        contact_persons=[],
        is_active=False,
    )

    entity = CounterpartyMapper.to_entity(model)

    assert entity.kpp is None
    assert entity.okpo is None
    assert entity.address is None
    assert entity.avatar_url is None
    assert entity.contact_persons == []


def test_from_entity_full_mapping(sample_counterparty_entity):

    model = CounterpartyMapper.from_entity(sample_counterparty_entity)

    assert model.id == sample_counterparty_entity.id
    assert model.created_at == sample_counterparty_entity.created_at
    assert model.updated_at == sample_counterparty_entity.updated_at
    assert model.counterparty_type == sample_counterparty_entity.counterparty_type
    assert model.name == sample_counterparty_entity.name
    assert model.legal_name == sample_counterparty_entity.legal_name
    assert model.inn == sample_counterparty_entity.inn.value
    assert model.kpp == sample_counterparty_entity.kpp.value
    assert model.okpo == sample_counterparty_entity.okpo.value
    assert model.phone == sample_counterparty_entity.phone.value
    assert model.email == sample_counterparty_entity.email
    assert model.address == sample_counterparty_entity.address
    assert model.avatar_url == sample_counterparty_entity.avatar_url
    assert model.is_active == sample_counterparty_entity.is_active

    assert model.contact_persons != []
    assert model.contact_persons[0]["full_name"] == (
        sample_counterparty_entity.contact_persons[0].full_name.value
    )
    assert model.contact_persons[0]["phone"] == \
           sample_counterparty_entity.contact_persons[0].phone.value
    assert model.contact_persons[0]["email"] == \
           sample_counterparty_entity.contact_persons[0].email
    assert model.contact_persons[0]["messengers"] == \
        sample_counterparty_entity.contact_persons[0].messengers


def test_from_entity_null_contact_person(sample_uuid, sample_datetime):

    entity = Counterparty(
        id=sample_uuid,
        created_at=sample_datetime,
        updated_at=sample_datetime,
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        okpo=Okpo("00123456"),
        phone=Phone("+79991234567"),
        email="info@romashka.ru",
        address="г. Москва, ул. Ленина, д. 10",
        avatar_url="https://example.com/logo.png",
        contact_persons=[],
        is_active=True,
    )

    model = CounterpartyMapper.from_entity(entity)

    assert model.contact_persons == []


def test_round_trip_consistency(sample_counterparty_model):

    entity = CounterpartyMapper.to_entity(sample_counterparty_model)
    model_back = CounterpartyMapper.from_entity(entity)

    assert model_back.id == sample_counterparty_model.id
    assert model_back.counterparty_type == sample_counterparty_model.counterparty_type
    assert model_back.name == sample_counterparty_model.name
    assert model_back.legal_name == sample_counterparty_model.legal_name
    assert model_back.inn == sample_counterparty_model.inn
    assert model_back.kpp == sample_counterparty_model.kpp
    assert model_back.okpo == sample_counterparty_model.okpo
    assert model_back.phone == sample_counterparty_model.phone
    assert model_back.email == sample_counterparty_model.email
    assert model_back.address == sample_counterparty_model.address
    assert model_back.avatar_url == sample_counterparty_model.avatar_url

    if model_back.contact_persons and sample_counterparty_model.contact_persons:
        assert model_back.contact_persons[0]["full_name"] == (
            sample_counterparty_model.contact_persons[0]["full_name"]
        )
        assert model_back.contact_persons[0]["phone"] == \
               sample_counterparty_model.contact_persons[0]["phone"]
        assert model_back.contact_persons[0]["email"] == \
               sample_counterparty_model.contact_persons[0]["email"]
