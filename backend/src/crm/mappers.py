from .domain.entities import Counterparty
from .schemas import ContactPersonOut, CounterpartyResponse


def map_counterparty_to_response(counterparty: Counterparty) -> CounterpartyResponse:
    """
    Преобразование доменной сущности контрагента к API схеме ответа
    """

    return CounterpartyResponse(
        id=counterparty.id,
        created_at=counterparty.created_at,
        updated_at=counterparty.updated_at,
        counterparty_type=counterparty.counterparty_type,
        name=counterparty.name,
        legal_name=counterparty.legal_name,
        inn=f"{counterparty.inn}",
        kpp=f"{counterparty.kpp}",
        okpo=f"{counterparty.okpo}",
        phone=f"{counterparty.phone}",
        email=counterparty.email,
        address=counterparty.address,
        avatar_url=counterparty.avatar_url,
        is_head=counterparty.is_head,
        parent_id=counterparty.parent_id,
        is_branch=counterparty.is_branch,
        is_active=counterparty.is_active,
        contact_persons=[
            ContactPersonOut(
                full_name=f"{contact_person.full_name}",
                phone=f"{contact_person.phone}",
                email=contact_person.email,
                messengers=contact_person.messengers,
            )
            for contact_person in counterparty.contact_persons
        ],
    )
