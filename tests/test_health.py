"""v1.1 渠道健康巡检：连续失败熔断 + 冷却恢复。"""
import asyncio

from sqlalchemy import select

from app.db.base import get_sessionmaker
from app.db.models import Channel
from app.domain.health import HealthService


def _run(coro):
    return asyncio.run(coro)


def test_circuit_breaker_trips_and_recovers(gateway):
    """连续失败达到阈值 → status=2 熔断；冷却后 try_recover → status=1。"""
    async def scenario():
        async with get_sessionmaker()() as s:
            ch = (await s.execute(select(Channel).where(Channel.name == "mock-deepseek"))).scalar_one()
            cid = ch.id

        health = HealthService(fail_threshold=3, cooldown=0.0)

        # 3 次失败 → 熔断
        for _ in range(3):
            await health.report(cid, False)
        async with get_sessionmaker()() as s:
            ch = (await s.execute(select(Channel).where(Channel.id == cid))).scalar_one()
            assert ch.status == 2
            assert ch.fail_count >= 3

        # 冷却为 0，立即可恢复
        recovered = await health.try_recover()
        assert recovered == 1
        async with get_sessionmaker()() as s:
            ch = (await s.execute(select(Channel).where(Channel.id == cid))).scalar_one()
            assert ch.status == 1
            assert ch.fail_count == 0

    _run(scenario())


def test_success_resets_fail_count(gateway):
    async def scenario():
        async with get_sessionmaker()() as s:
            ch = (await s.execute(select(Channel).where(Channel.name == "mock-deepseek"))).scalar_one()
            cid = ch.id
        health = HealthService(fail_threshold=5, cooldown=1.0)
        await health.report(cid, False)
        await health.report(cid, False)
        await health.report(cid, True)  # 成功清零
        async with get_sessionmaker()() as s:
            ch = (await s.execute(select(Channel).where(Channel.id == cid))).scalar_one()
            assert ch.fail_count == 0
            assert ch.status == 1

    _run(scenario())
