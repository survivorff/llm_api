"""用量记录与聚合。"""
from sqlalchemy import case, func, select
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

    async def query_logs(
        self, session: AsyncSession, *, limit: int = 50, offset: int = 0,
        user_id: int | None = None, token_name: str | None = None,
        model: str | None = None, channel: str | None = None,
        status: int | None = None, only_errors: bool = False,
        start: float | None = None, end: float | None = None,
    ) -> dict:
        """请求明细多维筛选 + 分页。返回 {total, items}。"""
        conds = []
        if user_id is not None:
            conds.append(UsageLog.user_id == user_id)
        if token_name:
            conds.append(UsageLog.token_name == token_name)
        if model:
            conds.append(UsageLog.model == model)
        if channel:
            conds.append(UsageLog.channel == channel)
        if status is not None:
            conds.append(UsageLog.status == status)
        if only_errors:
            conds.append(UsageLog.status >= 400)
        if start is not None:
            conds.append(UsageLog.ts >= start)
        if end is not None:
            conds.append(UsageLog.ts <= end)

        total = (
            await session.execute(select(func.count()).select_from(UsageLog).where(*conds))
        ).scalar_one()
        rows = (
            await session.execute(
                select(
                    UsageLog.id, UsageLog.ts, UsageLog.user_id, UsageLog.token_name,
                    UsageLog.model, UsageLog.upstream_model, UsageLog.channel,
                    UsageLog.status, UsageLog.latency_ms, UsageLog.prompt_tokens,
                    UsageLog.completion_tokens, UsageLog.total_tokens, UsageLog.cost,
                    UsageLog.stream, UsageLog.error,
                ).where(*conds).order_by(UsageLog.id.desc()).limit(limit).offset(offset)
            )
        ).all()
        return {"total": total, "items": [dict(r._mapping) for r in rows]}

    async def stats(self, session: AsyncSession, days: int = 7) -> dict:
        """概览统计：全期 + 今日 + 近 N 天 的请求数/tokens/消费/成功率。"""
        import time as _t

        def _agg_row(row):
            req = row.requests or 0
            ok = row.ok or 0
            return {
                "requests": req,
                "tokens": int(row.tokens or 0),
                "cost": int(row.cost or 0),
                "success_rate": round(ok / req * 100, 1) if req else 100.0,
            }

        def _q(*conds):
            return select(
                func.count().label("requests"),
                func.coalesce(func.sum(UsageLog.total_tokens), 0).label("tokens"),
                func.coalesce(func.sum(UsageLog.cost), 0).label("cost"),
                func.coalesce(func.sum(
                    case((UsageLog.status < 400, 1), else_=0)
                ), 0).label("ok"),
            ).where(*conds)

        now = _t.time()
        day_start = now - (now % 86400)  # 粗略当日起点（UTC）
        window_start = now - days * 86400

        total = _agg_row((await session.execute(_q())).one())
        today = _agg_row((await session.execute(_q(UsageLog.ts >= day_start))).one())
        window = _agg_row((await session.execute(_q(UsageLog.ts >= window_start))).one())
        return {"total": total, "today": today, "window": window, "days": days}
