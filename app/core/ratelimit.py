"""分布式限速器：优先 Redis 滑动窗口，无 Redis 时回退进程内存。

RPM（每分钟请求数）限制。多实例部署时必须用 Redis 才准确。
"""
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """抽象接口。"""

    async def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        raise NotImplementedError


class MemoryRateLimiter(RateLimiter):
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    async def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        if not limit or limit <= 0:
            return True
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


class RedisRateLimiter(RateLimiter):
    def __init__(self, redis) -> None:
        self._redis = redis

    async def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        if not limit or limit <= 0:
            return True
        now = time.time()
        rkey = f"rl:{key}"
        # 用有序集合做滑动窗口
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(rkey, 0, now - window)
        pipe.zcard(rkey)
        pipe.zadd(rkey, {f"{now}:{id(object())}": now})
        pipe.expire(rkey, int(window) + 1)
        _, count, _, _ = await pipe.execute()
        return count < limit
