"""运营与可观测端点（v2.0）。

公开：
- GET  /public/settings     站点公开设置（公告、站点名、语言）
- GET  /metrics             Prometheus 指标（可关）

管理（需 ADMIN_KEY）：
- GET/PUT /admin/settings    运营设置热更新
- GET     /admin/audit       审计日志查询
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import metrics
from ..core.state import AppServices
from ..db.base import get_session
from .deps import get_services, require_admin

# 公开路由（无鉴权）
public_router = APIRouter()
# 管理路由（需 admin）
admin_router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])

# 允许公开暴露的设置键
_PUBLIC_KEYS = ("announcement", "site_name", "topup_min")


@public_router.get("/public/settings")
async def public_settings(session: AsyncSession = Depends(get_session),
                          services: AppServices = Depends(get_services)):
    data = await services.settings_store.all(session)
    out = {k: data.get(k) for k in _PUBLIC_KEYS}
    out["default_language"] = services.settings.default_language
    return out


@public_router.get("/metrics")
async def prometheus_metrics(services: AppServices = Depends(get_services)):
    if not services.settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="metrics disabled")
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


@admin_router.get("/settings")
async def get_settings(session: AsyncSession = Depends(get_session),
                       services: AppServices = Depends(get_services)):
    return {"settings": await services.settings_store.all(session)}


@admin_router.put("/settings")
async def update_settings(request: Request, session: AsyncSession = Depends(get_session),
                          services: AppServices = Depends(get_services),
                          payload: dict = Body(default={})):
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="expected a JSON object of settings")
    await services.settings_store.set_many(session, payload)
    await services.audit.record(
        session, actor="admin", action="settings.update",
        detail={"keys": list(payload.keys())}, ip=request.client.host if request.client else None,
    )
    return {"settings": await services.settings_store.all(session)}


@admin_router.get("/audit")
async def audit_logs(session: AsyncSession = Depends(get_session),
                     services: AppServices = Depends(get_services),
                     limit: int = 200, action: str | None = None):
    return {"logs": await services.audit.recent(session, limit=limit, action=action)}
