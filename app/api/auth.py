"""账户与登录端点（Web 自助端）。

- POST /auth/register            邮箱注册 → 返回会话令牌
- POST /auth/login               邮箱登录 → 返回会话令牌
- GET  /auth/me                  当前用户信息（需会话）
- GET  /auth/providers           已启用的登录方式（邮箱/OAuth）
- GET  /auth/oauth/{provider}    发起 OAuth 授权跳转
- GET  /auth/oauth/{provider}/callback  OAuth 回调 → 会话令牌
- 自助令牌：GET/POST/DELETE /auth/tokens
- 自助账单：GET /auth/ledger, GET /auth/orders

会话令牌为 HMAC 签名的无状态 token；随 Authorization: Bearer 或 Cookie 提交。
"""
import secrets
import time

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.state import AppServices
from ..db.base import get_session
from ..db.models import BillingLedger, Order, Token, User
from ..domain.accounts import AccountError
from ..domain.oauth import OAuthError
from .deps import get_current_user, get_services

router = APIRouter(prefix="/auth")

# OAuth state 短期存储（防 CSRF）。单机内存即可；多实例可换 Redis。
_oauth_states: dict[str, float] = {}


def _user_dict(u: User) -> dict:
    return {"id": u.id, "username": u.username, "email": u.email, "role": u.role,
            "group": u.group, "balance": u.balance, "frozen": u.frozen}


@router.get("/providers")
async def providers(services: AppServices = Depends(get_services)):
    return {
        "email": services.settings.allow_registration,
        "oauth": sorted(services.oauth.keys()),
        "default_language": services.settings.default_language,
    }


@router.post("/register")
async def register(session: AsyncSession = Depends(get_session),
                   services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    try:
        user, token = await services.accounts.register(
            session, payload.get("email", ""), payload.get("password", ""),
            payload.get("username"),
        )
    except AccountError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return {"session": token, "user": _user_dict(user)}


@router.post("/login")
async def login(session: AsyncSession = Depends(get_session),
                services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    try:
        user, token = await services.accounts.login(
            session, payload.get("email", ""), payload.get("password", ""),
        )
    except AccountError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return {"session": token, "user": _user_dict(user)}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"user": _user_dict(user)}


# ---------------- OAuth ----------------
@router.get("/oauth/{provider}")
async def oauth_start(provider: str, services: AppServices = Depends(get_services)):
    prov = services.oauth.get(provider)
    if prov is None:
        raise HTTPException(status_code=404, detail="oauth provider not enabled")
    # 清理过期 state
    now = time.time()
    for s, ts in list(_oauth_states.items()):
        if now - ts > 600:
            _oauth_states.pop(s, None)
    state = secrets.token_urlsafe(24)
    _oauth_states[state] = now
    return {"authorize_url": prov.authorize_url(state)}


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request,
                         session: AsyncSession = Depends(get_session),
                         services: AppServices = Depends(get_services)):
    prov = services.oauth.get(provider)
    if prov is None:
        raise HTTPException(status_code=404, detail="oauth provider not enabled")
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state or state not in _oauth_states:
        raise HTTPException(status_code=400, detail="invalid oauth callback (code/state)")
    _oauth_states.pop(state, None)
    try:
        access_token = await prov.exchange_code(services.http, code)
        info = await prov.fetch_user(services.http, access_token)
        user, sess = await services.accounts.oauth_login(
            session, provider, info.sub, info.email, info.name,
        )
    except (OAuthError, AccountError) as e:
        detail = getattr(e, "detail", str(e))
        raise HTTPException(status_code=400, detail=detail)
    # 重定向回后台并带会话；也可改成前端约定的地址
    redirect = f"/admin?session={sess}"
    resp = RedirectResponse(url=redirect)
    resp.set_cookie("session", sess, httponly=True, max_age=int(services.settings.session_ttl_seconds),
                    samesite="lax")
    return resp


# ---------------- 自助令牌 ----------------
@router.get("/tokens")
async def my_tokens(session: AsyncSession = Depends(get_session),
                    services: AppServices = Depends(get_services),
                    user: User = Depends(get_current_user)):
    rows = await services.accounts.list_tokens(session, user.id)
    return {"tokens": [
        {"id": t.id, "key": t.key, "name": t.name, "enabled": t.enabled,
         "used_tokens": t.used_tokens, "quota_tokens": t.quota_tokens,
         "expires_at": t.expires_at, "created_at": t.created_at}
        for t in rows
    ]}


@router.post("/tokens")
async def create_my_token(session: AsyncSession = Depends(get_session),
                          services: AppServices = Depends(get_services),
                          user: User = Depends(get_current_user), payload: dict = Body(default={})):
    t = await services.accounts.create_token(session, user.id, payload.get("name", "token"))
    return {"id": t.id, "key": t.key, "name": t.name}


@router.delete("/tokens/{tid}")
async def delete_my_token(tid: int, session: AsyncSession = Depends(get_session),
                          user: User = Depends(get_current_user)):
    t = (await session.execute(select(Token).where(Token.id == tid))).scalar_one_or_none()
    if t is None or t.user_id != user.id:
        raise HTTPException(status_code=404, detail="token not found")
    await session.delete(t)
    await session.commit()
    return {"deleted": tid}


# ---------------- 自助账单 ----------------
@router.get("/ledger")
async def my_ledger(session: AsyncSession = Depends(get_session),
                    user: User = Depends(get_current_user), limit: int = 100):
    rows = (
        await session.execute(
            select(BillingLedger).where(BillingLedger.user_id == user.id)
            .order_by(BillingLedger.id.desc()).limit(limit)
        )
    ).scalars().all()
    return {"ledger": [
        {"id": r.id, "type": r.type, "amount": r.amount, "balance_after": r.balance_after,
         "ref": r.ref, "ts": r.ts}
        for r in rows
    ]}


@router.get("/orders")
async def my_orders(session: AsyncSession = Depends(get_session),
                    user: User = Depends(get_current_user), limit: int = 50):
    rows = (
        await session.execute(
            select(Order).where(Order.user_id == user.id)
            .order_by(Order.id.desc()).limit(limit)
        )
    ).scalars().all()
    return {"orders": [
        {"order_no": o.order_no, "status": o.status, "method": o.method,
         "amount_credits": o.amount_credits, "amount_money": o.amount_money,
         "currency": o.currency, "created_at": o.created_at, "paid_at": o.paid_at}
        for o in rows
    ]}
