"""鉴权服务：从请求令牌解析 principal（角色 / 用户 / 限制）。

角色：
- admin：ADMIN_KEY，管理后台
- token：数据库令牌，归属某用户，受启停/过期/配额/白名单限制
"""
import time
from dataclasses import dataclass, field

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Token, User


@dataclass
class Principal:
    kind: str                      # admin / token
    name: str
    user_id: int | None = None
    token_id: int | None = None
    group: str = "default"
    rpm_limit: int | None = None
    allowed_models: list[str] | None = None
    allowed_groups: list[str] | None = None
    quota_tokens: int | None = None
    used_tokens: int = 0
    expires_at: float | None = None
    balance: int = 0
    _extra: dict = field(default_factory=dict)


class AuthError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail


def extract_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key", "").strip()


def _split(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or None


class AuthService:
    def __init__(self, admin_key: str | None):
        self.admin_key = admin_key

    async def resolve(self, request: Request, session: AsyncSession) -> Principal:
        key = extract_key(request)
        if not key:
            raise AuthError(401, "missing api key")

        if self.admin_key and key == self.admin_key:
            return Principal(kind="admin", name="admin")

        token = (
            await session.execute(select(Token).where(Token.key == key))
        ).scalar_one_or_none()
        if token is None or not token.enabled:
            raise AuthError(401, "invalid or disabled api key")

        now = time.time()
        if token.expires_at and now > token.expires_at:
            raise AuthError(401, f"token expired for '{token.name}'")
        if token.quota_tokens is not None and token.used_tokens >= token.quota_tokens:
            raise AuthError(429, f"quota exceeded for '{token.name}'")

        user = (
            await session.execute(select(User).where(User.id == token.user_id))
        ).scalar_one_or_none()
        if user is None or user.status != 1:
            raise AuthError(401, "user disabled")

        return Principal(
            kind="token", name=token.name, user_id=user.id, token_id=token.id,
            group=user.group, rpm_limit=token.rpm_limit,
            allowed_models=_split(token.allowed_models),
            allowed_groups=_split(token.allowed_groups),
            quota_tokens=token.quota_tokens, used_tokens=token.used_tokens,
            expires_at=token.expires_at, balance=user.balance,
        )

    def verify_admin(self, request: Request) -> None:
        key = extract_key(request)
        if self.admin_key:
            if key != self.admin_key:
                raise AuthError(403, "admin access only")
        # 未设 admin_key：仅本地开发放行


__all__ = ["AuthService", "AuthError", "Principal", "extract_key"]
