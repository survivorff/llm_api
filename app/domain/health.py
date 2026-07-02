"""渠道健康巡检：连续失败自动熔断，冷却后自动恢复。

状态机（Channel.status）：
  1 = 正常  →  连续失败 >= fail_threshold  →  2 = 熔断
  2 = 熔断  →  距上次失败超过 cooldown 秒  →  1 = 半开（允许再次尝试）

report(channel_id, ok) 在每次转发后被调用（成功清零失败计数，失败累加）。
熔断的渠道在 Router 里被跳过（只读 status==1），因此自动生效。
"""
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_sessionmaker
from ..db.models import Channel


class HealthService:
    def __init__(self, fail_threshold: int = 5, cooldown: float = 60.0):
        self.fail_threshold = fail_threshold
        self.cooldown = cooldown
        self._last_fail: dict[int, float] = {}
        self.on_change = None  # 状态变更回调（如让路由缓存失效）

    def _notify(self) -> None:
        if callable(self.on_change):
            try:
                self.on_change()
            except Exception:
                pass

    async def report(self, channel_id: int, ok: bool) -> None:
        async with get_sessionmaker()() as session:
            ch = (
                await session.execute(select(Channel).where(Channel.id == channel_id))
            ).scalar_one_or_none()
            if ch is None:
                return
            if ok:
                if ch.fail_count or ch.status == 2:
                    changed = ch.status == 2
                    ch.fail_count = 0
                    if ch.status == 2:
                        ch.status = 1
                    await session.commit()
                    if changed:
                        self._notify()
            else:
                ch.fail_count = (ch.fail_count or 0) + 1
                self._last_fail[channel_id] = time.time()
                if ch.fail_count >= self.fail_threshold and ch.status == 1:
                    ch.status = 2  # 熔断
                    await session.commit()
                    self._notify()
                else:
                    await session.commit()

    async def try_recover(self) -> int:
        """巡检任务：把冷却期已过的熔断渠道恢复为半开（status=1）。返回恢复数量。"""
        now = time.time()
        recovered = 0
        async with get_sessionmaker()() as session:
            rows = (
                await session.execute(select(Channel).where(Channel.status == 2))
            ).scalars().all()
            for ch in rows:
                last = self._last_fail.get(ch.id, 0)
                if now - last >= self.cooldown:
                    ch.status = 1
                    ch.fail_count = 0
                    recovered += 1
            if recovered:
                await session.commit()
                self._notify()
        return recovered
