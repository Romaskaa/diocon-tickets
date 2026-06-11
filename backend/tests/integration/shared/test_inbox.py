from uuid import uuid4

import pytest
from sqlalchemy import select

from src.event_config import EVENT_TOPIC_MAP
from src.tickets.domain.events import TicketCreated
from src.shared.infra.inbox import InboxMessage, InboxRepository, MessageStatus

@pytest.fixture
def inbox_repo(session):
    return InboxRepository(session)


@pytest.mark.asyncio
async def test_add_returns_true_for_new_message(session, inbox_repo):
    """
    Проверяем сохранение нового inbox-сообщения: repository должен добавить
    событие в БД и вернуть True.
    Данные: уникальные message_id/event_type и payload события.
    """

    message_id = f"msg-{uuid4()}"
    event_type = EVENT_TOPIC_MAP[TicketCreated]
    payload = {
        "ticket_id": str(uuid4()),
        "title": "Test ticket"
    }

    created = await inbox_repo.add(message_id, event_type, payload)
    await session.commit()

    result = await session.execute(
        select(InboxMessage).where(
            InboxMessage.message_id == message_id,
            InboxMessage.event_type == event_type,
        )
    )
    message = result.scalar_one()

    assert created is True
    assert message.message_id == message_id
    assert message.event_type == event_type
    assert message.payload == payload
    assert message.status == MessageStatus.PENDING