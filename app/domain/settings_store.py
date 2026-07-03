"""运行时设置存储：DB 支持的可热更新键值配置（公告、注册开关、界面文案等）。

与 `config.Settings`（环境变量/启动期）互补：
- config.Settings：部署级、启动加载、含密钥。
- SettingsStore：运营级、可后台热更新、无需重启。

带进程内缓存，写入即失效。多实例可加 Redis pub/sub，这里先本地缓存。
"""
from __future__ import annotations

import json
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Setting

# 运营设置的默认值（DB 无记录时回退）
DEFAULTS: dict = {
    "announcement": "",          # 首页公告（纯文本/markdown）
    "site_name": "llm_api",      # 站点名
    "allow_registration": True,  # 运行时注册开关（覆盖 env 默认）
    "topup_min": 1,              # 最小充值额（展示用）
}


class SettingsStore:
    def __init__(self, ttl: float = 10.0):
        self._cache: dict | None = None
        self._at: float = 0.0
        self._ttl = ttl

    async def _load(self, session: AsyncSession) -> dict:
        rows = (await session.execute(select(Setting))).scalars().all()
        data = dict(DEFAULTS)
        for r in rows:
            try:
                data[r.key] = json.loads(r.value)
            except Exception:
                data[r.key] = r.value
        return data

    async def all(self, session: AsyncSession) -> dict:
        now = time.time()
        if self._cache is None or now - self._at > self._ttl:
            self._cache = await self._load(session)
            self._at = now
        return dict(self._cache)

    async def get(self, session: AsyncSession, key: str, default=None):
        data = await self.all(session)
        return data.get(key, DEFAULTS.get(key, default))

    async def set(self, session: AsyncSession, key: str, value) -> None:
        row = (
            await session.execute(select(Setting).where(Setting.key == key))
        ).scalar_one_or_none()
        payload = json.dumps(value, ensure_ascii=False)
        if row is None:
            session.add(Setting(key=key, value=payload))
        else:
            row.value = payload
        await session.commit()
        self.invalidate()

    async def set_many(self, session: AsyncSession, values: dict) -> None:
        for k, v in values.items():
            row = (
                await session.execute(select(Setting).where(Setting.key == k))
            ).scalar_one_or_none()
            payload = json.dumps(v, ensure_ascii=False)
            if row is None:
                session.add(Setting(key=k, value=payload))
            else:
                row.value = payload
        await session.commit()
        self.invalidate()

    def invalidate(self) -> None:
        self._cache = None
        self._at = 0.0
