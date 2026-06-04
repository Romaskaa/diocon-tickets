from redis.asyncio import Redis

from .settings import settings

redis_client = Redis(
    host=settings.redis.host,
    port=settings.redis.port,
    db=settings.redis.db,
    decode_responses=True,
)
