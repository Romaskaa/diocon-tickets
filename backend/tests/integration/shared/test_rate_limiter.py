import pytest
from redis.asyncio import Redis

from src.shared.infra.rate_limiter import RateLimiter


@pytest.fixture
def redis_client(redis_url):
    return Redis.from_url(redis_url)


@pytest.mark.asyncio
async def test_sliding_window_logic(redis_client):
    """
    Тестирование логики скользящего окна
    """

    limiter = RateLimiter(redis_client)
    client_id = "test_id"
    max_requests = 2
    window_seconds = 60
    endpoint = "/tests"

    r1 = await limiter.check_limit(
        client_id=client_id,
        endpoint=endpoint,
        max_requests=max_requests,
        window_seconds=window_seconds
    )
    assert r1.allowed is True
    assert r1.remaining == 1

    r2 = await limiter.check_limit(
        client_id=client_id,
        endpoint=endpoint,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    assert r2.allowed is True
    assert r2.remaining == 0

    r3 = await limiter.check_limit(
        client_id=client_id,
        endpoint=endpoint,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    assert r3.allowed is False
