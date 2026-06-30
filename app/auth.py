"""鉴权：
- 网关访问(verify_gateway)：admin key / owner key / 数据库令牌，含启用、过期、配额校验。
- 后台管理(verify_admin)：仅 admin key（未设则回退 owner key / 本地放行）。
"""
import time

from fastapi import HTTPException, Request


def get_client_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key", "").strip()


def _parse_models(raw):
    if not raw:
        return None
    return [m.strip() for m in str(raw).split(",") if m.strip()]


def verify_gateway(request: Request, config: dict, db) -> dict:
    """返回 principal: {kind, name, token_id, rpm_limit, allowed_models, ...}。"""
    token = get_client_key(request)
    admin_key = config["auth"].get("admin_key")
    owner_keys = config["auth"].get("client_keys") or []

    if not token:
        if not admin_key and not owner_keys and not db.list_tokens():
            return {"kind": "anon", "name": "anonymous", "token_id": None,
                    "rpm_limit": None, "allowed_models": None}
        raise HTTPException(status_code=401, detail="missing api key")

    if admin_key and token == admin_key:
        return {"kind": "admin", "name": "admin", "token_id": None,
                "rpm_limit": None, "allowed_models": None}
    if token in owner_keys:
        return {"kind": "owner", "name": "owner", "token_id": None,
                "rpm_limit": None, "allowed_models": None}

    row = db.get_token_by_key(token)
    if row and row["enabled"]:
        now = time.time()
        if row.get("expires_at") and now > row["expires_at"]:
            raise HTTPException(status_code=401, detail=f"token expired for '{row['name']}'")
        if row["quota_tokens"] is not None and row["used_tokens"] >= row["quota_tokens"]:
            raise HTTPException(status_code=429, detail=f"quota exceeded for '{row['name']}'")
        return {
            "kind": "token", "name": row["name"], "token_id": row["id"],
            "rpm_limit": row.get("rpm_limit"),
            "allowed_models": _parse_models(row.get("allowed_models")),
            "used_tokens": row["used_tokens"], "quota_tokens": row["quota_tokens"],
            "expires_at": row.get("expires_at"),
        }

    raise HTTPException(status_code=401, detail="invalid or disabled api key")


def verify_admin(request: Request, config: dict) -> bool:
    token = get_client_key(request)
    admin_key = config["auth"].get("admin_key")
    owner_keys = config["auth"].get("client_keys") or []

    if admin_key:
        if token == admin_key:
            return True
        raise HTTPException(status_code=403, detail="admin access only")
    # 未设 admin_key：回退用 owner key
    if owner_keys:
        if token in owner_keys:
            return True
        raise HTTPException(status_code=403, detail="admin access only")
    # 全本地无鉴权
    return True
