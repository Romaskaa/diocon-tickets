from typing import Annotated

from datetime import datetime

from fastapi import Depends, Query, Request
from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.broker import broker
from src.core.database import get_db
from src.core.redis import redis_client
from src.core.settings import settings

from ..event_config import EVENT_TOPIC_MAP
from .domain.dtos import TimeRangeFilters
from .domain.events import EventPublisher
from .domain.exceptions import RateLimitExceededError
from .infra.events import FastStreamEventPublisher
from .infra.mail import SmtpMailSender
from .infra.rate_limiter import IdentifierFunc, RateLimiter, ip_identifier
from .infra.spellchecking import LanguageToolSpellChecker, SpellChecker
from .infra.sse import SSEManager
from .schemas import Pagination

sse_manager = SSEManager()

SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_pagination(
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
) -> Pagination:
    return Pagination(page=page, size=size)


def get_time_range_filters(
        created_after: Annotated[datetime | None, Query(description="Создан после")] = None,
        created_before: Annotated[datetime | None, Query(description="Создан до")] = None,
) -> TimeRangeFilters:
    return TimeRangeFilters(created_after=created_after, created_before=created_before)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]
TimeRangeFiltersDep = Annotated[TimeRangeFilters, Depends(get_time_range_filters)]


def get_event_publisher() -> FastStreamEventPublisher:
    return FastStreamEventPublisher(broker, event_topic_map=EVENT_TOPIC_MAP)


EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]


def get_spell_checker() -> SpellChecker:
    return LanguageToolSpellChecker(
        language=settings.language_tool.language, remote_server=settings.language_tool.url
    )


SpellCheckerDep = Annotated[SpellChecker, Depends(get_spell_checker)]


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
