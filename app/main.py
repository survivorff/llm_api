"""FastAPI 应用入口：OpenAI 兼容的多用户 LLM 网关 + 后台管理。"""
import contextlib
import os
import time

import httpx
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from . import auth, proxy
from .admin_ui import ADMIN_HTML
from .config import load_config
from .ratelimit import RateLimiter
from .router import NoChannelError, Router
from .store import Database


def _expires_from_payload(payload: dict):
    if payload.get("expires_at") is not None:
        return payload["expires_at"]
    days = payload.get("expires_in_days")
    if days:
        return time.time() + float(days) * 86400
    return None


def _allowed_models_from_payload(payload: dict):
    am = payload.get("allowed_models")
    if isinstance(am, list):
        return ",".join(m.strip() for m in am if str(m).strip()) or None
    if isinstance(am, str):
        return am.strip() or None
    return None


def create_app(config: dict) -> FastAPI:
    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http = httpx.AsyncClient()
        app.state.store = Database(config["logging"]["db_path"])
        app.state.router = Router(config)
        app.state.limiter = RateLimiter()
        app.state.config = config
        if not config["auth"].get("admin_key") and not config["auth"].get("client_keys"):
            print("⚠️  未配置 admin_key / client_keys：处于本地无鉴权模式，仅限本机自用！"
                  "给朋友用或上服务器前，务必设置 ADMIN_KEY。")
        try:
            yield
        finally:
            await app.state.http.aclose()

    app = FastAPI(title="llm_api gateway", lifespan=lifespan)

    # ---------------- 网关接口（OpenAI 兼容） ----------------
    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "channels": [c["name"] for c in config["channels"]]}

    @app.get("/v1/models")
    async def models(request: Request):
        auth.verify_gateway(request, config, app.state.store)
        data = [{"id": m, "object": "model", "owned_by": cn}
                for m, cn in app.state.router.list_models()]
        return {"object": "list", "data": data}

    @app.get("/v1/me")
    async def whoami(request: Request):
        """令牌持有者自助查询：用量 / 剩余配额 / 有效期。"""
        p = auth.verify_gateway(request, config, app.state.store)
        if p["kind"] != "token":
            return {"name": p["name"], "role": p["kind"], "unlimited": True}
        quota = p.get("quota_tokens")
        used = p.get("used_tokens") or 0
        return {
            "name": p["name"], "role": "token",
            "used_tokens": used, "quota_tokens": quota,
            "remaining_tokens": None if quota is None else max(quota - used, 0),
            "rpm_limit": p.get("rpm_limit"), "expires_at": p.get("expires_at"),
            "allowed_models": p.get("allowed_models"),
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        principal = auth.verify_gateway(request, config, app.state.store)
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid JSON body")
        model = payload.get("model")
        if not model:
            raise HTTPException(status_code=400, detail="missing 'model'")

        # 模型白名单（仅对朋友令牌生效）
        allowed = principal.get("allowed_models")
        if principal["kind"] == "token" and allowed is not None and model not in allowed:
            raise HTTPException(status_code=403, detail=f"model '{model}' not allowed for this token")

        # 限速（每令牌 RPM）
        rpm = principal.get("rpm_limit")
        if rpm and principal.get("token_id"):
            if not app.state.limiter.allow(principal["token_id"], rpm):
                raise HTTPException(status_code=429, detail="rate limit exceeded (RPM)")

        try:
            attempts = app.state.router.resolve(model)
        except NoChannelError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return await proxy.forward(app, attempts, payload, bool(payload.get("stream")), principal)

    # ---------------- 后台管理接口（需 admin） ----------------
    @app.get("/admin/tokens")
    async def list_tokens(request: Request):
        auth.verify_admin(request, config)
        return {"tokens": app.state.store.list_tokens()}

    @app.post("/admin/tokens")
    async def create_token(request: Request, payload: dict = Body(default={})):
        auth.verify_admin(request, config)
        return app.state.store.create_token(
            name=(payload.get("name") or "friend").strip(),
            quota_tokens=payload.get("quota_tokens"),
            note=payload.get("note"),
            expires_at=_expires_from_payload(payload),
            rpm_limit=payload.get("rpm_limit"),
            allowed_models=_allowed_models_from_payload(payload),
        )

    @app.patch("/admin/tokens/{tid}")
    async def update_token(tid: int, request: Request, payload: dict = Body(default={})):
        auth.verify_admin(request, config)
        if app.state.store.get_token_by_id(tid) is None:
            raise HTTPException(status_code=404, detail="token not found")
        fields = {}
        for k in ("enabled", "quota_tokens", "rpm_limit", "name", "note"):
            if k in payload:
                fields[k] = payload[k]
        if "expires_at" in payload or "expires_in_days" in payload:
            fields["expires_at"] = _expires_from_payload(payload)
        if "allowed_models" in payload:
            fields["allowed_models"] = _allowed_models_from_payload(payload)
        return app.state.store.update_token(tid, **fields)

    @app.delete("/admin/tokens/{tid}")
    async def delete_token(tid: int, request: Request):
        auth.verify_admin(request, config)
        app.state.store.delete_token(tid)
        return {"deleted": tid}

    @app.get("/admin/usage")
    async def usage(request: Request):
        auth.verify_admin(request, config)
        store = app.state.store
        return {
            "by_channel": store.summary_by_channel(),
            "by_token": store.summary_by_token(),
            "recent": store.recent(100),
        }

    @app.get("/admin", response_class=HTMLResponse)
    @app.get("/admin/ui", response_class=HTMLResponse)
    async def admin_ui():
        return HTMLResponse(ADMIN_HTML)

    return app


def app_factory() -> FastAPI:
    """供 `uvicorn app.main:app_factory --factory` 使用的零参工厂。"""
    return create_app(load_config(os.environ.get("CONFIG_PATH", "config.yaml")))


def main():
    config = load_config(os.environ.get("CONFIG_PATH", "config.yaml"))
    app = create_app(config)
    import uvicorn
    uvicorn.run(app, host=config["server"]["host"], port=int(config["server"]["port"]))


if __name__ == "__main__":
    main()
