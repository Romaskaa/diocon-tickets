from faststream.rabbit import RabbitBroker
from faststream.rabbit.fastapi import RabbitRouter

from .settings import settings

broker_router = RabbitRouter(url=settings.rabbit.url)


def get_broker() -> RabbitBroker:
    return broker_router.broker


broker = get_broker()
