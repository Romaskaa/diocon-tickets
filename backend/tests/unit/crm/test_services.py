# Тестирование Use cases

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.crm.domain.vo import CounterpartyType
from src.crm.schemas import BranchAdd, ContactPersonIn, CounterpartyCreate
from src.crm.services import CounterpartyService
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def legal_entity_data():
    return CounterpartyCreate(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="Головная компания",
        legal_name="ООО Головная компания",
        inn="1234567890",
        kpp="123456789",
        phone="88005553535",
        email="parent@example.com",
        address="Москва, ул. Ленина, д.1",
        contact_persons=[ContactPersonIn(
            first_name="Иван",
            last_name="Иванов",
            middle_name="Иванович",
            phone="88005553535",
            email="ivanov@example.com",
        )],
    )


@pytest.fixture
def branch_data():
    return BranchAdd(
        name="Филиал",
        legal_name="ООО Головная компания (филиал)",
        kpp="987654321",
        phone="88005553536",
        email="branch@example.com",
        address="Санкт-Петербург, Невский пр., д.10",
    )


@pytest.fixture
def counterparty_service(mock_session, mock_counterparty_repo):
    return CounterpartyService(session=mock_session, repository=mock_counterparty_repo)


# ====================== Тесты для сервисов контрагента ======================


@pytest.mark.asyncio
async def test_create_counterparty_success(legal_entity_data, mock_counterparty_repo):
    service = CounterpartyService(session=AsyncMock(), repository=mock_counterparty_repo)

    response = await service.create(legal_entity_data)

    assert response.id is not None


@pytest.mark.asyncio
async def test_add_branch_to_exists_counterparty(
        legal_entity_data, branch_data, mock_counterparty_repo
):
    service = CounterpartyService(session=AsyncMock(), repository=mock_counterparty_repo)

    counterparty = await service.create(legal_entity_data)
    response = await service.add_branch(counterparty.id, branch_data)

    assert response.id is not None


@pytest.mark.asyncio
async def test_add_contact_person_to_exists_counterparty(
        legal_entity_data, counterparty_service, mock_session
):
    created_response = await counterparty_service.create(legal_entity_data)

    data = ContactPersonIn(
        first_name="Иван",
        last_name="Иванов",
        middle_name="Иванович",
        phone="88005553535",
        email="ivanov.ivan@example.com",
    )
    response = await counterparty_service.add_contact_person(created_response.id, data)

    assert response.contact_persons != []


@pytest.mark.asyncio
async def test_fails_add_contact_person_to_not_exists_counterparty(counterparty_service):
    data = ContactPersonIn(
        first_name="Иван",
        last_name="Иванов",
        middle_name="Иванович",
        phone="88005553535",
        email="ivanov.ivan@example.com",
    )

    with pytest.raises(NotFoundError):
        await counterparty_service.add_contact_person(uuid4(), data)
