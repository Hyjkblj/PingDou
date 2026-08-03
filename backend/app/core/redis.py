from functools import lru_cache

import redis.asyncio as aioredis
import redis as sync_redis

from app.core.config import get_settings


@lru_cache
def get_async_redis() -> aioredis.Redis:
    settings = get_settings()
    return aioredis.from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_sync_redis() -> sync_redis.Redis:
    settings = get_settings()
    return sync_redis.from_url(settings.redis_url, decode_responses=True)
