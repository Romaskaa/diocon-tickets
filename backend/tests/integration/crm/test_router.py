import pytest
from fastapi import status


@pytest.fixture
def legal_entity_payload():
    return {
        "counterparty_type": "Юридическое лицо",
        "name": "Головная компания",
        "legal_name": "ООО Головная компания",
        "inn": "1234567890",
        "kpp": "123456789",
        "phone": "88005553535",
        "email": "parent@example.com",
        "address": "Москва, ул. Ленина, д.1",
        "contact_persons": [{
            "first_name": "Иван",
            "last_name": "Иванов",
            "middle_name": "Иванович",
            "phone": "88005553535",
            "email": "ivanov@example.com",
        }],
    }


@pytest.fixture
def branch_payload():
    return {
        "name": "Филиал",
        "legal_name": "ООО Головная компания (филиал)",
        "kpp": "987654321",
        "phone": "88005553536",
        "email": "branch@example.com",
        "address": "Санкт-Петербург, Невский пр., д.10",
    }


@pytest.mark.asyncio
async def test_create_counterparty(client, legal_entity_payload):
    # 1. Создание
    response = await client.post(url="/api/v1/counterparties", json=legal_entity_payload)

    assert response.status_code == status.HTTP_201_CREATED

    counterparty_id = response.json()["id"]

    # 2. Получение через API
    response = await client.get(url=f"/api/v1/counterparties/{counterparty_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["phone"] == "+7 (800) 555-35-35"


@pytest.mark.asyncio
async def test_add_branch_counterparty(client, legal_entity_payload, branch_payload):
    # 1. Создание основного контрагента
    response = await client.post(url="/api/v1/counterparties", json=legal_entity_payload)

    assert response.status_code == status.HTTP_201_CREATED

    counterparty_id = response.json()["id"]

    # 2. Добавление филиала
    response = await client.post(
        url=f"/api/v1/counterparties/{counterparty_id}", json=branch_payload
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["phone"] == "+7 (800) 555-35-36"
