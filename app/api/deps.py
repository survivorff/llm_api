"""FastAPI 依赖：获取共享服务、当前 principal。"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.state import AppServices
from ..db.base import get_session
from ..db.models import User
from ..domain.auth import AuthError, Principal


def get_services(request: Request) -> AppServices:
    return request.app.state.services


def _session_token(request: Request) -> str:
    """从 Authorization: Bearer 或 Cookie 提取会话令牌。"""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get("session", "").strip()


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
) -> User:
    """Web 自助端身份：校验 HMAC 会话令牌 → 返回 User。"""
    token = _session_token(request)
    payload = services.accounts.verify(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="login required")
    user = (
        await session.execute(select(User).where(User.id == payload.get("uid")))
    ).scalar_one_or_none()
    if user is None or user.status != 1:
        raise HTTPException(status_code=401, detail="account not found or disabled")
    return user


async def get_user_id(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
) -> int:
    """解析充值主体的 user_id：优先会话令牌，其次绑定用户的 API 令牌。

    这样 Web 登录用户（会话）和 API 令牌持有者都能充值。
    """
    token = _session_token(request)
    payload = services.accounts.verify(token) if token else None
    if payload:
        user = (
            await session.execute(select(User).where(User.id == payload.get("uid")))
        ).scalar_one_or_none()
        if user and user.status == 1:
            return user.id
    # 回退到 API 令牌身份
    try:
        principal = await services.auth.resolve(request, session)
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    if not principal.user_id:
        raise HTTPException(status_code=403, detail="a user-bound identity is required")
    return principal.user_id


async def get_principal(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
) -> Principal:
    try:
        return await services.auth.resolve(request, session)
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


def require_admin(request: Request, services: AppServices = Depends(get_services)) -> None:
    try:
        services.auth.verify_admin(request)
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
