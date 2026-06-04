import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from faststream.rabbit import RabbitBroker

from ...tickets.domain.events import TicketCreated
from ..domain.events import Event

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self, max_queue_size: int = 1000) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue_size)
        self._handlers: dict[
            type[Event], list[Callable[[Event], Awaitable[None] | None]]
        ] = defaultdict(list)
        self._task: asyncio.Task | None = None
        self._is_running = False

    def subscribe(self, event_type: type[Event], handler: Callable) -> None:
        """Подписка обработчика на событие"""

        self._handlers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        """Публикация события (добавление в очередь)"""

        try:
            await self._queue.put(event)
        except asyncio.QueueFull:
            logger.exception("EventBus queue is full! Dropping event: %s", type(event).__name__)

    async def publish_all(self, events: list[Event]) -> None:
        """Публикация списка событий (удобно после сохранения агрегата)"""

        for event in events:
            await self.publish(event)

    async def _dispatch(self, event: Event) -> None:
        """Вызов всех обработчиков для данного события"""

        handlers = self._handlers.get(type(event), [])

        if not handlers:
            logger.debug("No handlers registered for event: %s", type(event).__name__)
            return

        for handler in handlers:
            # noinspection PyBroadException
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                logger.exception(
                    "Error in handler %s for event %s",
                    handler.__name__ if hasattr(handler, "__name__") else str(handler),
                    type(event).__name__,
                )

    async def _process_events(self) -> None:
        """Основной цикл обработки событий из очереди"""

        while self._is_running:
            # noinspection PyBroadException
            try:
                event = await self._queue.get()
                await self._dispatch(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unexpected error in EventBus processing loop")

    async def start(self) -> None:
        """Запуск обработчика событий в фоне"""

        if self._is_running:
            return

        self._is_running = True
        self._task = asyncio.create_task(self._process_events())
        logger.info("EventBus started")

    async def stop(self) -> None:
        """Остановка обработчика"""

        self._is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.exception("Error occurred while task stopping")
        logger.info("EventBus stopped")


# Маппинг доменных событий к топикам в которых они будут обработаны (очереди)
EVENT_TOPIC_MAP: dict[type[Event], str] = {
    TicketCreated: "tickets.create"
}


class FastStreamEventPublisher:
    def __init__(self, broker: RabbitBroker) -> None:
        self.broker = broker

    async def publish(self, event: Event) -> None:
        topic = EVENT_TOPIC_MAP.get(type(event))
        if topic is None:
            logger.warning(
                "Domain event `%s` was not handled! No such topic registered.",
                type(event).__name__
            )
            return
        await self.broker.publish(event, queue=topic)

    async def publish_all(self, events: list[Event]) -> None:
        for event in events:
            await self.publish(event)
