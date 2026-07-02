"""FastAPI 应用入口：OpenAI 兼容的多用户 LLM 网关 + 计费 + 后台管理（v1 架构）。"""
import contextlib
import os

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .api import admin as admin_api
from .api import v1 as v1_api
from .bootstrap import bootstrap
from .config import Settings, get_settings
from .core.cache import create_redis
from .core.state import AppServices
from .db.base import dispose_engine, init_engine
from .web.admin_ui import ADMIN_HTML


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
        try:
            yield
        finally:
            await http.aclose()
            if redis:
                await redis.aclose()
            await dispose_engine()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    app.include_router(v1_api.router)
    app.include_router(admin_api.router)

    @app.get("/admin", response_class=HTMLResponse)
    @app.get("/admin/ui", response_class=HTMLResponse)
    async def admin_ui():
        return HTMLResponse(ADMIN_HTML)

    return app


def app_factory() -> FastAPI:
    return create_app()


def main():
    settings = get_settings()
    app = create_app(settings)
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
