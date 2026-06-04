import json
from datetime import timedelta
from uuid import UUID

from redis.asyncio import Redis

from ...shared.utils.time import current_datetime


class RedisTokenBlacklist:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def revoke(self, jti: UUID, user_id: UUID, exp: int, reason: str) -> bool:
        # 1. Расчёт TTL и проверка токена на действительность
        now = int(current_datetime().timestamp())
        ttl = exp - now
        if ttl <= 0:
            return False  # Токен уже истёк

        # 2. Сохранение токена
        ttl = timedelta(seconds=ttl)
        key = f"blacklist:jti:{jti}"
        value = json.dumps({"revoked_at": now, "user_id": f"{user_id}", "reason": reason})
        await self.redis.setex(key, ttl, value)
        return True

    async def is_revoked(self, jti: UUID) -> bool:
        key = f"blacklist:jti:{jti}"
        is_exists = await self.redis.exists(key)
        return bool(is_exists)
