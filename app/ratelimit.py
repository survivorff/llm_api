"""极简内存限速器：每个令牌按 RPM（每分钟请求数）滑动窗口限制。"""
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key, rpm: int, window: float = 60.0) -> bool:
        if not rpm or rpm <= 0:
            return True
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= rpm:
                return False
            q.append(now)
            return True
