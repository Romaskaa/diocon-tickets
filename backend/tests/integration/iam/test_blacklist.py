import json
from datetime import timedelta
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from src.iam.infra.blacklist import RedisTokenBlacklist
from src.shared.utils.time import current_datetime, get_expiration_timestamp


@pytest.fixture
def redis_client(redis_url):
    return Redis.from_url(redis_url)


@pytest.fixture
def redis_token_blacklist(redis_client):
    return RedisTokenBlacklist(redis_client)


class TestRedisTokenBlacklist:
    @pytest.mark.asyncio
    async def test_revoke_and_is_revoked(self, redis_token_blacklist):
        jti, user_id = uuid4(), uuid4()
        exp = get_expiration_timestamp(timedelta(hours=1))
        reason = "test_logout"

        # 1. Отзыв токена
        success = await redis_token_blacklist.revoke(jti, user_id=user_id, exp=exp, reason=reason)
        assert success is True

        # 2. Проверка, что токен в blacklist
        is_revoked = await redis_token_blacklist.is_revoked(jti)
        assert is_revoked is True

    @pytest.mark.asyncio
    async def test_revoke_expired_token_returns_false(self, redis_token_blacklist):
        jti, user_id = uuid4(), uuid4()
        exp = int((current_datetime() - timedelta(minutes=5)).timestamp())
        reason = "test_logout"

        success = await redis_token_blacklist.revoke(jti, user_id=user_id, exp=exp, reason=reason)
        assert success is False

    @pytest.mark.asyncio
    async def test_is_revoked_returns_false_for_unknown_jti(self, redis_token_blacklist):
        unknown_jti = uuid4()
        is_revoked = await redis_token_blacklist.is_revoked(unknown_jti)
        assert is_revoked is False

    @pytest.mark.asyncio
    async def test_value_stored_correctly(self, redis_token_blacklist, redis_client):
        jti, user_id = uuid4(), uuid4()
        exp = get_expiration_timestamp(timedelta(minutes=30))
        reason = "security_compromise"

        await redis_token_blacklist.revoke(jti, user_id=user_id, exp=exp, reason=reason)

        key = f"blacklist:jti:{jti}"
        raw_value = await redis_client.get(key)
        assert raw_value is not None

        data = json.loads(raw_value)
        assert "revoked_at" in data
        assert data["user_id"] == str(user_id)
        assert data["reason"] == reason
