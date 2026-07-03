"""路由服务：模型名 → 渠道，生成带 key 轮询 + 加权 + 故障转移的 attempt 列表。

从 DB 读取 channels（缓存在内存，带 TTL），支持：
- 匹配优先级：精确 → 前缀(claude-*) → 通配(*)
- 分组过滤（令牌可限制可用分组）
- 加权随机 + priority 排序
- 熔断渠道(status=2)跳过
"""
import json
import random
import threading
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.security import decrypt_secret, key_fingerprint as _fp
from ..db.models import Channel


class NoChannelError(Exception):
    pass


class Attempt:
    __slots__ = ("channel", "channel_id", "type", "base_url", "upstream_model", "api_key", "headers", "key_fp")

    def __init__(self, channel, channel_id, type_, base_url, upstream_model, api_key, headers, key_fp=None):
        self.channel = channel
        self.channel_id = channel_id
        self.type = type_
        self.base_url = base_url
        self.upstream_model = upstream_model
        self.api_key = api_key
        self.headers = headers or {}
        self.key_fp = key_fp

    @property
    def url(self) -> str:
        return f"{self.base_url}/chat/completions"


def _is_prefix(pattern: str, model: str) -> bool:
    return pattern.endswith("*") and pattern != "*" and model.startswith(pattern[:-1])


def _weighted_shuffle(channels: list[dict]) -> list[dict]:
    """按 weight 做加权随机排序：weight 越大越可能排在前面。

    实现：对每个渠道取 key = random()^(1/weight)，降序排列（加权随机采样）。
    """
    scored = []
    for c in channels:
        w = max(c.get("weight", 1), 1)
        r = random.random() or 1e-12
        scored.append((r ** (1.0 / w), c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


class Router:
    def __init__(self, cache_ttl: float = 10.0, crypto_secret: str | None = None) -> None:
        self._rr: dict[int, int] = {}
        self._lock = threading.Lock()
        self._cache: list[dict] | None = None
        self._cache_ts = 0.0
        self._ttl = cache_ttl
        self._crypto_secret = crypto_secret

    async def _channels(self, session: AsyncSession) -> list[dict]:
        now = time.time()
        if self._cache is not None and now - self._cache_ts < self._ttl:
            return self._cache
        rows = (await session.execute(select(Channel).where(Channel.status == 1))).scalars().all()
        secret = self._crypto_secret or get_settings().crypto_secret
        out = []
        for c in rows:
            try:
                meta = json.loads(c.key_meta or "{}")
            except Exception:
                meta = {}
            keys = []
            for enc in json.loads(c.api_keys or "[]"):
                k = decrypt_secret(enc, secret)
                if not k:
                    continue
                fp = _fp(k)
                if meta.get(fp, {}).get("disabled"):
                    continue  # 跳过被禁用的 key
                keys.append((k, fp))
            if not keys:
                continue
            out.append({
                "id": c.id, "name": c.name, "type": c.type,
                "base_url": c.base_url.rstrip("/"), "api_keys": keys,
                "models": json.loads(c.models or "[]"),
                "model_map": json.loads(c.model_map or "{}"),
                "headers": json.loads(c.headers or "{}"),
                "group": c.group, "weight": max(c.weight, 1), "priority": c.priority,
            })
        self._cache = out
        self._cache_ts = now
        return out

    def invalidate(self) -> None:
        self._cache = None

    def _next_key_index(self, channel_id: int, n: int) -> int:
        with self._lock:
            i = self._rr.get(channel_id, 0)
            self._rr[channel_id] = (i + 1) % n
        return i % n

    async def resolve(self, session: AsyncSession, model: str, allowed_groups: list[str] | None = None):
        channels = await self._channels(session)
        if allowed_groups:
            channels = [c for c in channels if c["group"] in allowed_groups]

        exact, prefix, wildcard = [], [], []
        for c in channels:
            models = c["models"]
            if model in models:
                exact.append(c)
            elif any(_is_prefix(m, model) for m in models):
                prefix.append(c)
            elif "*" in models:
                wildcard.append(c)

        def order(bucket):
            # priority 升序（小优先），同 priority 内按 weight 加权随机排序
            groups: dict[int, list] = {}
            for c in bucket:
                groups.setdefault(c["priority"], []).append(c)
            out = []
            for prio in sorted(groups):
                out.extend(_weighted_shuffle(groups[prio]))
            return out

        chosen, seen = [], set()
        for c in order(exact) + order(prefix) + order(wildcard):
            if c["id"] not in seen:
                seen.add(c["id"])
                chosen.append(c)
        if not chosen:
            raise NoChannelError(f"no channel configured for model '{model}'")

        attempts = []
        for c in chosen:
            n = len(c["api_keys"])
            start = self._next_key_index(c["id"], n)
            upstream = c["model_map"].get(model, model)
            for j in range(n):
                key, fp = c["api_keys"][(start + j) % n]
                attempts.append(
                    Attempt(c["name"], c["id"], c["type"], c["base_url"], upstream, key, c["headers"], fp)
                )
        return attempts

    async def list_models(self, session: AsyncSession):
        channels = await self._channels(session)
        out, seen = [], set()
        for c in channels:
            names = [m for m in c["models"] if m != "*" and not m.endswith("*")]
            names += list(c["model_map"].keys())
            for m in names:
                if m not in seen:
                    seen.add(m)
                    out.append((m, c["name"]))
        return out
