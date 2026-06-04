from faststream.rabbit import RabbitBroker

from .settings import settings

broker = RabbitBroker(url=settings.rabbit.url)
