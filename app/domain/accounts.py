"""账户服务：邮箱注册/登录、会话签发、OAuth 绑定、自助令牌管理。

- 注册：邮箱唯一，密码 bcrypt 哈希。首个注册用户自动成为 admin（可关）。
- 登录：校验密码 → 签发 HMAC 会话令牌。
- OAuth：以 provider+sub 唯一标识，找到或创建用户后签发会话。
- 会话身份与网关 API key 独立；自助端用会话，转发用 API key。
"""
from __future__ import annotations

import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import hash_password, new_token_key, verify_password
from ..core.sessions import issue_session, verify_session
from ..db.models import OAuthAccount, Token, User


class AccountError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail


class AccountService:
    def __init__(self, session_secret: str, session_ttl: float = 7 * 86400,
                 allow_registration: bool = True):
        self.secret = session_secret
        self.ttl = session_ttl
        self.allow_registration = allow_registration

    # ---------------- 注册 / 登录 ----------------
    async def register(self, session: AsyncSession, email: str, password: str,
                       username: str | None = None) -> tuple[User, str]:
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            raise AccountError(400, "valid email required")
        if len(password or "") < 6:
            raise AccountError(400, "password must be at least 6 chars")
        if not self.allow_registration:
            raise AccountError(403, "registration disabled")

        exists = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if exists:
            raise AccountError(409, "email already registered")

        username = (username or email.split("@")[0]).strip()
        # 用户名唯一化
        base = username
        i = 1
        while (await session.execute(select(User).where(User.username == username))).scalar_one_or_none():
            i += 1
            username = f"{base}{i}"

        # 首个用户成为 admin
        total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        role = "admin" if total == 0 else "user"

        user = User(username=username, email=email, password_hash=hash_password(password),
                    role=role, group="default", balance=0)
        session.add(user)
        await session.commit()
        return user, self._session_for(user)

    async def login(self, session: AsyncSession, email: str, password: str) -> tuple[User, str]:
        email = (email or "").strip().lower()
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if user is None or not user.password_hash or not verify_password(password, user.password_hash):
            raise AccountError(401, "invalid email or password")
        if user.status != 1:
            raise AccountError(403, "account disabled")
        return user, self._session_for(user)

    # ---------------- OAuth ----------------
    async def oauth_login(self, session: AsyncSession, provider: str, sub: str,
                          email: str | None = None, name: str | None = None) -> tuple[User, str]:
        """按 (provider, sub) 找绑定账号；没有则创建新用户并绑定。"""
        link = (
            await session.execute(
                select(OAuthAccount).where(
                    OAuthAccount.provider == provider, OAuthAccount.sub == str(sub)
                )
            )
        ).scalar_one_or_none()
        if link is not None:
            user = (await session.execute(select(User).where(User.id == link.user_id))).scalar_one_or_none()
            if user is None:
                raise AccountError(401, "linked user missing")
            if user.status != 1:
                raise AccountError(403, "account disabled")
            return user, self._session_for(user)

        # 邮箱已存在则绑定到该用户，否则新建
        user = None
        if email:
            user = (
                await session.execute(select(User).where(User.email == email.lower()))
            ).scalar_one_or_none()
        if user is None:
            username = (name or f"{provider}_{sub}").strip()[:60]
            base, i = username, 1
            while (await session.execute(select(User).where(User.username == username))).scalar_one_or_none():
                i += 1
                username = f"{base}{i}"
            total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
            role = "admin" if total == 0 else "user"
            user = User(username=username, email=(email or None), role=role,
                        group="default", balance=0)
            session.add(user)
            await session.flush()

        session.add(OAuthAccount(provider=provider, sub=str(sub), user_id=user.id,
                                 email=email, created_at=time.time()))
        await session.commit()
        return user, self._session_for(user)

    # ---------------- 会话 ----------------
    def _session_for(self, user: User) -> str:
        return issue_session(user.id, self.secret, ttl=self.ttl, role=user.role)

    def verify(self, token: str) -> dict | None:
        return verify_session(token, self.secret)

    # ---------------- 自助令牌 ----------------
    async def create_token(self, session: AsyncSession, user_id: int, name: str) -> Token:
        t = Token(user_id=user_id, key=new_token_key(), name=(name or "token").strip())
        session.add(t)
        await session.commit()
        return t

    async def list_tokens(self, session: AsyncSession, user_id: int) -> list[Token]:
        return list(
            (await session.execute(select(Token).where(Token.user_id == user_id).order_by(Token.id)))
            .scalars().all()
        )
