"""OAuth2 登录（可插拔）：GitHub / Google / LinuxDO 等标准 OAuth2 provider。

统一三步：
- authorize_url：拼接授权跳转 URL（带 state 防 CSRF）
- exchange_code：用 code 换 access_token
- fetch_user：用 access_token 取用户信息，归一成 (sub, email, name)

每个 provider 只是端点 URL + 字段映射的差异，用配置表驱动。
core 不绑定任何一家；部署者在 OAUTH_PROVIDERS 里配 client_id/secret 即启用。
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

# 各 provider 的端点与用户字段映射
_PROVIDER_SPECS = {
    "github": {
        "authorize": "https://github.com/login/oauth/authorize",
        "token": "https://github.com/login/oauth/access_token",
        "userinfo": "https://api.github.com/user",
        "scope": "read:user user:email",
        "sub_field": "id",
        "email_field": "email",
        "name_field": "login",
    },
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
        "sub_field": "id",
        "email_field": "email",
        "name_field": "name",
    },
    "linuxdo": {
        "authorize": "https://connect.linux.do/oauth2/authorize",
        "token": "https://connect.linux.do/oauth2/token",
        "userinfo": "https://connect.linux.do/api/user",
        "scope": "",
        "sub_field": "id",
        "email_field": "email",
        "name_field": "username",
    },
}


@dataclass
class OAuthUser:
    sub: str
    email: str | None = None
    name: str | None = None


class OAuthError(Exception):
    pass


class OAuthProvider:
    def __init__(self, name: str, config: dict):
        if name not in _PROVIDER_SPECS:
            raise OAuthError(f"unsupported oauth provider '{name}'")
        self.name = name
        self.spec = _PROVIDER_SPECS[name]
        self.config = config or {}

    @property
    def client_id(self) -> str:
        return self.config.get("client_id", "")

    @property
    def client_secret(self) -> str:
        return self.config.get("client_secret", "")

    @property
    def redirect_uri(self) -> str:
        return self.config.get("redirect_uri", "")

    def authorize_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.config.get("scope", self.spec["scope"]),
            "state": state,
        }
        return f"{self.spec['authorize']}?{urlencode(params)}"

    async def exchange_code(self, client: httpx.AsyncClient, code: str) -> str:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        resp = await client.post(self.spec["token"], data=data,
                                 headers={"Accept": "application/json"}, timeout=15.0)
        try:
            payload = resp.json()
        except Exception:
            raise OAuthError("token endpoint returned non-JSON")
        token = payload.get("access_token")
        if not token:
            raise OAuthError(payload.get("error_description") or "no access_token")
        return token

    async def fetch_user(self, client: httpx.AsyncClient, access_token: str) -> OAuthUser:
        resp = await client.get(
            self.spec["userinfo"],
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=15.0,
        )
        if resp.status_code >= 400:
            raise OAuthError(f"userinfo failed: {resp.status_code}")
        data = resp.json()
        sub = data.get(self.spec["sub_field"])
        if sub is None:
            raise OAuthError("userinfo missing sub field")
        return OAuthUser(
            sub=str(sub),
            email=data.get(self.spec["email_field"]),
            name=data.get(self.spec["name_field"]),
        )


def build_oauth_providers(config: dict) -> dict[str, OAuthProvider]:
    out: dict[str, OAuthProvider] = {}
    for name, cfg in (config or {}).items():
        if name in _PROVIDER_SPECS and isinstance(cfg, dict) and cfg.get("client_id"):
            out[name] = OAuthProvider(name, cfg)
    return out
