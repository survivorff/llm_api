"""Redis 客户端封装：可选。无 REDIS_URL 时返回 None，调用方回退内存实现。"""
from __future__ import annotations


async def create_redis(redis_url: str | None):
    if not redis_url:
        return None
    try:
        import redis.asyncio as aioredis
    except ImportError:
        return None
    client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    try:
        await client.ping()
    except Exception:
        return None
    return client
