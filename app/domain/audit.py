"""审计日志服务：记录管理操作与敏感事件，支持查询与保留策略清理。"""
from __future__ import annotations

import json
import time

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AuditLog


class AuditService:
    def __init__(self, retention_days: float = 90.0):
        self.retention_days = retention_days

    async def record(self, session: AsyncSession, actor: str, action: str,
                     target: str | None = None, detail: dict | None = None,
                     ip: str | None = None) -> None:
        session.add(AuditLog(
            actor=actor, action=action, target=target,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            ip=ip, ts=time.time(),
        ))
        await session.commit()

    async def recent(self, session: AsyncSession, limit: int = 200,
                     action: str | None = None) -> list[dict]:
        q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
        if action:
            q = q.where(AuditLog.action == action)
        rows = (await session.execute(q)).scalars().all()
        return [
            {"id": r.id, "ts": r.ts, "actor": r.actor, "action": r.action,
             "target": r.target, "detail": r.detail, "ip": r.ip}
            for r in rows
        ]

    async def purge_old(self, session: AsyncSession) -> int:
        """删除超过保留期的日志，返回删除数量。"""
        if self.retention_days <= 0:
            return 0
        cutoff = time.time() - self.retention_days * 86400
        result = await session.execute(delete(AuditLog).where(AuditLog.ts < cutoff))
        await session.commit()
        return result.rowcount or 0
