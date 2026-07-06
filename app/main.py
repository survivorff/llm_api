"""FastAPI 应用入口：OpenAI 兼容的多用户 LLM 网关 + 计费 + 后台管理（v1 架构）。"""
import asyncio
import contextlib
import os

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .api import admin as admin_api
from .api import auth as auth_api
from .api import ops as ops_api
from .api import pay as pay_api
from .api import v1 as v1_api
from .bootstrap import bootstrap
from .config import Settings, get_settings
from .core.cache import create_redis
from .core.state import AppServices
from .db.base import dispose_engine, init_engine
from .web.admin_ui import ADMIN_HTML
from .web.portal_ui import PORTAL_HTML
from .web.site_docs import docs_html
from .web.site_home import home_html
from .web.site_models import models_html
from .web.site_pricing import pricing_html


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        # SQLite 需要 data 目录
        if settings.is_sqlite:
            os.makedirs("data", exist_ok=True)
        init_engine(settings.database_url)
        await bootstrap(settings)

        http = httpx.AsyncClient(trust_env=settings.http_trust_env)
        redis = await create_redis(settings.redis_url)
        app.state.services = AppServices.build(settings, http, redis)

        if not settings.admin_key:
            print("⚠️  未配置 ADMIN_KEY：后台无鉴权，仅限本机开发！上线前务必设置。")

        # 后台任务：渠道健康巡检 + 支付对账 + 审计日志清理
        health_task = asyncio.create_task(_health_loop(app.state.services, settings))
        reconcile_task = asyncio.create_task(_reconcile_loop(app.state.services, settings))
        audit_task = asyncio.create_task(_audit_purge_loop(app.state.services, settings))
        try:
            yield
        finally:
            for task in (health_task, reconcile_task, audit_task):
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            await http.aclose()
            if redis:
                await redis.aclose()
            await dispose_engine()

    app = FastAPI(title=settings.app_name, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    app.include_router(v1_api.router)
    app.include_router(auth_api.router)
    app.include_router(pay_api.router)
    app.include_router(ops_api.public_router)
    app.include_router(ops_api.admin_router)
    app.include_router(admin_api.router)

    @app.get("/admin", response_class=HTMLResponse)
    @app.get("/admin/ui", response_class=HTMLResponse)
    async def admin_ui():
        return HTMLResponse(ADMIN_HTML)

    @app.get("/", response_class=HTMLResponse)
    async def home_page():
        return HTMLResponse(home_html())

    @app.get("/docs", response_class=HTMLResponse)
    async def docs_page():
        return HTMLResponse(docs_html())

    @app.get("/models", response_class=HTMLResponse)
    async def models_page():
        return HTMLResponse(models_html())

    @app.get("/pricing", response_class=HTMLResponse)
    async def pricing_page():
        return HTMLResponse(pricing_html())

    @app.get("/portal", response_class=HTMLResponse)
    async def portal_ui():
        return HTMLResponse(PORTAL_HTML)

    return app


async def _health_loop(services: AppServices, settings: Settings) -> None:
    """定期尝试恢复冷却期已过的熔断渠道。"""
    interval = max(settings.channel_health_interval, 5.0)
    while True:
        try:
            await asyncio.sleep(interval)
            await services.health.try_recover()
        except asyncio.CancelledError:
            break
        except Exception:
            continue


async def _reconcile_loop(services: AppServices, settings: Settings) -> None:
    """支付对账 worker：轮询 pending 订单主动查询 provider，并过期陈旧订单。

    仅在有支付 provider 时运行；无 provider 直接退出。
    """
    if not services.payments:
        return
    interval = max(settings.reconcile_interval, 5.0)
    from sqlalchemy import select

    from .db.base import get_sessionmaker
    from .db.models import Order
    while True:
        try:
            await asyncio.sleep(interval)
            async with get_sessionmaker()() as session:
                await services.orders.expire_stale(session)
                pend = (
                    await session.execute(
                        select(Order).where(Order.status == "pending").limit(50)
                    )
                ).scalars().all()
                for order in pend:
                    with contextlib.suppress(Exception):
                        await services.orders.reconcile_one(session, order)
        except asyncio.CancelledError:
            break
        except Exception:
            continue


async def _audit_purge_loop(services: AppServices, settings: Settings) -> None:
    """定期清理超过保留期的审计日志（每 6 小时）。"""
    if settings.audit_retention_days <= 0:
        return
    from .db.base import get_sessionmaker
    while True:
        try:
            await asyncio.sleep(6 * 3600)
            async with get_sessionmaker()() as session:
                await services.audit.purge_old(session)
        except asyncio.CancelledError:
            break
        except Exception:
            continue


def app_factory() -> FastAPI:
    return create_app()


def main():
    settings = get_settings()
    app = create_app(settings)
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
