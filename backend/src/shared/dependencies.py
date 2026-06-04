from typing import Annotated

from fastapi import Depends, Query, Request
from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.redis import redis_client
from ..core.settings import settings
from .domain.events import EventPublisher
from .domain.exceptions import RateLimitExceededError
from .infra.events import EventBus
from .infra.mail import SmtpMailSender
from .infra.rate_limiter import IdentifierFunc, RateLimiter, ip_identifier
from .infra.websocket import WebsocketManager
from .schemas import PageParams

event_bus = EventBus()

ws_manager = WebsocketManager()

SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_page_params(
    page: Annotated[
        PositiveInt,
        Query(
            ge=1,
            description="Номер страницы (начинается с 1)",
            examples=[1],
        ),
    ] = 1,
    size: Annotated[
        PositiveInt,
        Query(
            ge=1,
            le=100,
            description="Количество элементов на странице (от 1 до 100)",
            examples=[20],
        ),
    ] = 10,
) -> PageParams:
    return PageParams(page=page, size=size)


PageParamsDep = Annotated[PageParams, Depends(get_page_params)]


def get_event_publisher() -> EventPublisher:
    return event_bus


EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]


def get_mail_sender() -> SmtpMailSender:
    return SmtpMailSender(
        smtp_port=settings.mail.smtp_port,
        smtp_host=settings.mail.smtp_host,
        use_tls=settings.mail.smtp_use_tls,
    )


def get_rate_limiter() -> RateLimiter:
    return RateLimiter(redis_client)


def create_rate_limiter(
        max_requests: int, window_seconds: int, identifier: IdentifierFunc = ip_identifier
):
    """Создание зависимости для проверки лимита запросов"""

    async def dependency(request: Request, limiter: RateLimiter = Depends(get_rate_limiter)):
        client_id = await identifier(request)
        endpoint = request.url.path

        result = await limiter.check_limit(
            client_id=client_id,
            endpoint=endpoint,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if not result.allowed:
            raise RateLimitExceededError(
                "Too many requests",
                details={
                    "Retry_after": "",
                    "X-RateLimit-Limit": f"{max_requests}",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": f"{int(result.reset_at)}",
                },
            )

        return result

    return dependency
