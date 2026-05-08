import asyncio
from uuid import uuid4

import pytest

from src.shared.infra.sse import SSEManager


@pytest.mark.asyncio
async def test_sse_manager_sends_message_to_all_user_queues():
    """
    SSE manager доставляет сообщение во все локальные очереди пользователя.
    Это основной сценарий fan-out для уведомлений.
    """
    manager = SSEManager()
    user_id = uuid4()
    first_queue = asyncio.Queue()
    second_queue = asyncio.Queue()
    message = {"type": "ticket_updated", "ticket_id": str(uuid4())}

    await manager.connect(user_id, first_queue)
    await manager.connect(user_id, second_queue)

    await manager.send_to_user(user_id, message)

    assert await first_queue.get() == message
    assert await second_queue.get() == message


@pytest.mark.asyncio
async def test_sse_manager_disconnect_removes_queue():
    """
    SSE manager удаляет очередь при disconnect и больше не отправляет туда события.
    """
    manager = SSEManager()
    user_id = uuid4()
    queue = asyncio.Queue()

    await manager.connect(user_id, queue)
    await manager.disconnect(user_id, queue)
    await manager.send_to_user(user_id, {"type": "ticket_updated"})

    assert user_id not in manager.local_queues
    assert queue.empty()
