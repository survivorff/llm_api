"""用量记录与聚合。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Token, UsageLog


class UsageService:
    async def log(self, session: AsyncSession, **kw) -> None:
        session.add(UsageLog(**kw))
        await session.commit()

    async def add_token_usage(self, session: AsyncSession, token_id: int | None, tokens: int | None) -> None:
        if not token_id or not tokens:
            return
        tok = (await session.execute(select(Token).where(Token.id == token_id))).scalar_one_or_none()
        if tok:
            tok.used_tokens += tokens
            await session.commit()

    async def summary_by_channel(self, session: AsyncSession) -> list[dict]:
        rows = (
            await session.execute(
                select(
                    UsageLog.channel,
                    func.count().label("requests"),
                    func.coalesce(func.sum(UsageLog.total_tokens), 0).label("tokens"),
                    func.coalesce(func.sum(UsageLog.cost), 0).label("cost"),
                    func.round(func.avg(UsageLog.latency_ms)).label("avg_latency_ms"),
                ).group_by(UsageLog.channel)
            )
        ).all()
        return [dict(r._mapping) for r in rows]

    async def summary_by_user(self, session: AsyncSession) -> list[dict]:
        rows = (
            await session.execute(
                select(
                    func.coalesce(UsageLog.token_name, "(unknown)").label("token_name"),
                    func.count().label("requests"),
                    func.coalesce(func.sum(UsageLog.total_tokens), 0).label("tokens"),
                    func.coalesce(func.sum(UsageLog.cost), 0).label("cost"),
                ).group_by(UsageLog.token_name).order_by(func.sum(UsageLog.total_tokens).desc())
            )
        ).all()
        return [dict(r._mapping) for r in rows]

    async def recent(self, session: AsyncSession, limit: int = 100) -> list[dict]:
        rows = (
            await session.execute(
                select(
                    UsageLog.ts, UsageLog.model, UsageLog.channel, UsageLog.status,
                    UsageLog.latency_ms, UsageLog.total_tokens, UsageLog.cost,
                    UsageLog.stream, UsageLog.token_name,
                ).order_by(UsageLog.id.desc()).limit(limit)
            )
        ).all()
        return [dict(r._mapping) for r in rows]
