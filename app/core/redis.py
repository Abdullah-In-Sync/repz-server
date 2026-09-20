from typing import Any

import redis.asyncio as redis

from app.core.config import settings

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def cache_get(key: str) -> str | None:
    try:
        client = await get_redis()
        value = await client.get(key)
        if value is None:
            return None
        return value if isinstance(value, str) else value.decode()
    except Exception:
        return None


async def cache_set(key: str, value: str, ttl: int) -> None:
    try:
        client = await get_redis()
        await client.set(key, value, ex=ttl)
    except Exception:
        return


async def cache_delete(*keys: str) -> None:
    if not keys:
        return
    client = await get_redis()
    await client.delete(*keys)


async def ping_redis() -> bool:
    try:
        client = await get_redis()
        return bool(await client.ping())
    except Exception:
        return False


async def json_cache_get(key: str) -> Any | None:
    import json

    raw = await cache_get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def json_cache_set(key: str, value: Any, ttl: int) -> None:
    import json

    await cache_set(key, json.dumps(value, default=str), ttl)
