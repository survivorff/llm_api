"""会话令牌：HMAC 签名的无状态 session token（不引入 JWT 依赖）。

结构：base64url(payload_json).base64url(hmac_sha256(payload, secret))
payload 含 uid / exp（epoch 秒）。校验签名 + 过期即可，无需服务端存储。

用途：Web 自助端（注册/登录后）的身份凭证，走 Authorization: Bearer <session>
或 Cookie。与网关 API key 完全独立（API key 用于 /v1 转发）。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(payload_b64: str, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256)
    return _b64e(mac.digest())


def issue_session(user_id: int, secret: str, ttl: float = 7 * 86400, **extra) -> str:
    payload = {"uid": user_id, "exp": time.time() + ttl}
    payload.update(extra)
    payload_b64 = _b64e(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{payload_b64}.{_sign(payload_b64, secret)}"


def verify_session(token: str, secret: str) -> dict | None:
    """校验签名与过期，返回 payload；无效返回 None。"""
    if not token or token.count(".") != 1:
        return None
    payload_b64, sig = token.split(".", 1)
    expect = _sign(payload_b64, secret)
    if not hmac.compare_digest(sig, expect):
        return None
    try:
        payload = json.loads(_b64d(payload_b64))
    except Exception:
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload
