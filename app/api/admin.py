"""后台管理端点（需 ADMIN_KEY）：用户 / 令牌 / 渠道 / 定价 / 用量。"""
import json
import time

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.security import encrypt_secret, new_token_key
from ..core.state import AppServices
from ..db.base import get_session
from ..db.models import Channel, ModelPricing, Order, RedemptionCode, Token, User
from .deps import get_services, require_admin

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


# ---------------- users ----------------
@router.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(User).order_by(User.id))).scalars().all()
    return {"users": [_user_dict(u) for u in rows]}


@router.post("/users")
async def create_user(session: AsyncSession = Depends(get_session), payload: dict = Body(default={})):
    username = (payload.get("username") or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")
    exists = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="username exists")
    u = User(
        username=username, email=payload.get("email"), role=payload.get("role", "user"),
        group=payload.get("group", "default"), balance=int(payload.get("balance") or 0),
    )
    session.add(u)
    await session.commit()
    return _user_dict(u)


@router.patch("/users/{uid}")
async def update_user(uid: int, session: AsyncSession = Depends(get_session), payload: dict = Body(default={})):
    u = (await session.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if u is None:
        raise HTTPException(status_code=404, detail="user not found")
    for k in ("email", "role", "group", "status"):
        if k in payload:
            setattr(u, k, payload[k])
    await session.commit()
    return _user_dict(u)


@router.post("/users/{uid}/topup")
async def topup(uid: int, session: AsyncSession = Depends(get_session),
                services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    amount = int(payload.get("amount") or 0)
    if amount == 0:
        raise HTTPException(status_code=400, detail="amount required")
    u = await services.billing.topup(session, uid, amount, ref="admin-manual", type_="adjust")
    if u is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _user_dict(u)


# ---------------- tokens ----------------
@router.get("/tokens")
async def list_tokens(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Token).order_by(Token.id))).scalars().all()
    return {"tokens": [_token_dict(t) for t in rows]}


@router.post("/tokens")
async def create_token(session: AsyncSession = Depends(get_session), payload: dict = Body(default={})):
    user_id = payload.get("user_id")
    if not user_id:
        # 无指定用户：绑定到第一个 admin 用户，方便快速创建
        admin = (await session.execute(select(User).order_by(User.id))).scalars().first()
        if admin is None:
            raise HTTPException(status_code=400, detail="no user exists; create a user first")
        user_id = admin.id
    t = Token(
        user_id=user_id, key=new_token_key(), name=(payload.get("name") or "friend").strip(),
        quota_tokens=payload.get("quota_tokens"), note=payload.get("note"),
        rpm_limit=payload.get("rpm_limit"),
        allowed_models=_models_str(payload.get("allowed_models")),
        allowed_groups=_models_str(payload.get("allowed_groups")),
        expires_at=_expires(payload),
    )
    session.add(t)
    await session.commit()
    return _token_dict(t, reveal=True)


@router.patch("/tokens/{tid}")
async def update_token(tid: int, session: AsyncSession = Depends(get_session), payload: dict = Body(default={})):
    t = (await session.execute(select(Token).where(Token.id == tid))).scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="token not found")
    for k in ("name", "note", "quota_tokens", "rpm_limit"):
        if k in payload:
            setattr(t, k, payload[k])
    if "enabled" in payload:
        t.enabled = 1 if payload["enabled"] else 0
    if "allowed_models" in payload:
        t.allowed_models = _models_str(payload["allowed_models"])
    if "allowed_groups" in payload:
        t.allowed_groups = _models_str(payload["allowed_groups"])
    if "expires_at" in payload or "expires_in_days" in payload:
        t.expires_at = _expires(payload)
    await session.commit()
    return _token_dict(t)


@router.delete("/tokens/{tid}")
async def delete_token(tid: int, session: AsyncSession = Depends(get_session)):
    t = (await session.execute(select(Token).where(Token.id == tid))).scalar_one_or_none()
    if t:
        await session.delete(t)
        await session.commit()
    return {"deleted": tid}


# ---------------- channels ----------------
@router.get("/channels")
async def list_channels(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Channel).order_by(Channel.id))).scalars().all()
    return {"channels": [_channel_dict(c) for c in rows]}


@router.post("/channels")
async def create_channel(session: AsyncSession = Depends(get_session),
                         services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    secret = services.settings.crypto_secret
    keys = payload.get("api_keys") or []
    enc = [encrypt_secret(str(k).strip(), secret) for k in keys if str(k).strip()]
    c = Channel(
        name=payload.get("name") or "channel", type=payload.get("type") or "openai",
        base_url=(payload.get("base_url") or "").rstrip("/"),
        api_keys=json.dumps(enc), models=json.dumps(payload.get("models") or []),
        model_map=json.dumps(payload.get("model_map") or {}),
        headers=json.dumps(payload.get("headers") or {}),
        group=payload.get("group", "default"), weight=int(payload.get("weight") or 1),
        priority=int(payload.get("priority") or 0),
    )
    session.add(c)
    await session.commit()
    services.router.invalidate()
    return _channel_dict(c)


@router.patch("/channels/{cid}")
async def update_channel(cid: int, session: AsyncSession = Depends(get_session),
                         services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    c = (await session.execute(select(Channel).where(Channel.id == cid))).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="channel not found")
    secret = services.settings.crypto_secret
    for k in ("name", "type", "group", "weight", "priority", "status"):
        if k in payload:
            setattr(c, k, payload[k])
    if "base_url" in payload:
        c.base_url = payload["base_url"].rstrip("/")
    if "api_keys" in payload:
        enc = [encrypt_secret(str(k).strip(), secret) for k in payload["api_keys"] if str(k).strip()]
        c.api_keys = json.dumps(enc)
    for k, col in (("models", "models"), ("model_map", "model_map"), ("headers", "headers")):
        if k in payload:
            setattr(c, col, json.dumps(payload[k]))
    await session.commit()
    services.router.invalidate()
    return _channel_dict(c)


@router.delete("/channels/{cid}")
async def delete_channel(cid: int, session: AsyncSession = Depends(get_session),
                         services: AppServices = Depends(get_services)):
    c = (await session.execute(select(Channel).where(Channel.id == cid))).scalar_one_or_none()
    if c:
        await session.delete(c)
        await session.commit()
        services.router.invalidate()
    return {"deleted": cid}


# ---------------- channel account pool (v2.3) ----------------
@router.get("/channels/{cid}/keys")
async def channel_keys(cid: int, session: AsyncSession = Depends(get_session),
                       services: AppServices = Depends(get_services)):
    """渠道内 key 池的脱敏摘要（指纹/掩码/启停/统计）。"""
    c = (await session.execute(select(Channel).where(Channel.id == cid))).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="channel not found")
    return {"keys": services.channels.key_summaries(c)}


@router.post("/channels/{cid}/keys/{fp}/toggle")
async def toggle_channel_key(cid: int, fp: str, session: AsyncSession = Depends(get_session),
                             services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    """启停渠道内的某个 key（按指纹）。"""
    disabled = bool(payload.get("disabled"))
    ok = await services.channels.set_key_disabled(session, cid, fp, disabled)
    if not ok:
        raise HTTPException(status_code=404, detail="channel not found")
    services.router.invalidate()
    return {"ok": True, "fp": fp, "disabled": disabled}


@router.post("/channels/{cid}/test")
async def test_channel(cid: int, request: Request, session: AsyncSession = Depends(get_session),
                       services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    """连通性测试：发极小请求，返回每个 key 的 ok/延迟/错误。"""
    res = await services.channels.test(
        session, cid, services.http,
        model=payload.get("model"), all_keys=bool(payload.get("all_keys")),
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    await services.audit.record(
        session, actor="admin", action="channel.test", target=str(cid),
        ip=request.client.host if request.client else None,
    )
    return res


@router.get("/channels/{cid}/discover-models")
async def discover_models(cid: int, session: AsyncSession = Depends(get_session),
                          services: AppServices = Depends(get_services)):
    """从上游拉取可用模型列表（OpenAI 兼容渠道）。"""
    res = await services.channels.discover_models(session, cid, services.http)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


# ---------------- pricing ----------------
@router.get("/pricing")
async def list_pricing(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(ModelPricing).order_by(ModelPricing.id))).scalars().all()
    return {"pricing": [_pricing_dict(p) for p in rows]}


@router.post("/pricing")
async def create_pricing(session: AsyncSession = Depends(get_session), payload: dict = Body(default={})):
    p = ModelPricing(
        model=payload["model"], group=payload.get("group", "default"),
        input_price=int(payload.get("input_price") or 0),
        output_price=int(payload.get("output_price") or 0),
        cache_price=payload.get("cache_price"),
        multiplier=float(payload.get("multiplier") or 1.0),
    )
    session.add(p)
    await session.commit()
    return _pricing_dict(p)


@router.patch("/pricing/{pid}")
async def update_pricing(pid: int, session: AsyncSession = Depends(get_session), payload: dict = Body(default={})):
    p = (await session.execute(select(ModelPricing).where(ModelPricing.id == pid))).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="pricing not found")
    for k in ("model", "group", "input_price", "output_price", "cache_price", "multiplier", "enabled"):
        if k in payload:
            setattr(p, k, payload[k])
    await session.commit()
    return _pricing_dict(p)


@router.delete("/pricing/{pid}")
async def delete_pricing(pid: int, session: AsyncSession = Depends(get_session)):
    p = (await session.execute(select(ModelPricing).where(ModelPricing.id == pid))).scalar_one_or_none()
    if p:
        await session.delete(p)
        await session.commit()
    return {"deleted": pid}


# ---------------- usage ----------------
@router.get("/usage")
async def usage(session: AsyncSession = Depends(get_session), services: AppServices = Depends(get_services)):
    return {
        "by_channel": await services.usage.summary_by_channel(session),
        "by_token": await services.usage.summary_by_user(session),
        "recent": await services.usage.recent(session, 100),
    }


# ---------------- groups (v2.3) ----------------
@router.get("/groups")
async def list_groups(session: AsyncSession = Depends(get_session)):
    """聚合用户分组与定价分组：每个分组的用户数、定价条数。"""
    from sqlalchemy import func as _f
    u_rows = (await session.execute(
        select(User.group, _f.count()).group_by(User.group)
    )).all()
    p_rows = (await session.execute(
        select(ModelPricing.group, _f.count()).group_by(ModelPricing.group)
    )).all()
    c_rows = (await session.execute(
        select(Channel.group, _f.count()).group_by(Channel.group)
    )).all()
    groups: dict[str, dict] = {}
    for g, n in u_rows:
        groups.setdefault(g or "default", {})["users"] = n
    for g, n in p_rows:
        groups.setdefault(g or "default", {})["pricing"] = n
    for g, n in c_rows:
        groups.setdefault(g or "default", {})["channels"] = n
    out = [{"group": g, "users": v.get("users", 0), "pricing": v.get("pricing", 0),
            "channels": v.get("channels", 0)} for g, v in sorted(groups.items())]
    return {"groups": out}


# ---------------- orders & redemption (v1.2) ----------------
@router.get("/orders")
async def list_orders(session: AsyncSession = Depends(get_session), limit: int = 100):
    rows = (
        await session.execute(select(Order).order_by(Order.id.desc()).limit(limit))
    ).scalars().all()
    return {"orders": [_order_dict(o) for o in rows]}


@router.get("/payment-methods")
async def payment_methods(services: AppServices = Depends(get_services)):
    """已启用的支付方式（供后台/前端展示）。"""
    return {"methods": sorted(services.payments.keys())}


@router.post("/redemption/generate")
async def generate_redemption(session: AsyncSession = Depends(get_session),
                              services: AppServices = Depends(get_services),
                              payload: dict = Body(default={})):
    amount = int(payload.get("amount_credits") or 0)
    count = int(payload.get("count") or 1)
    if amount <= 0 or count <= 0 or count > 1000:
        raise HTTPException(status_code=400, detail="invalid amount or count (1-1000)")
    codes = await services.orders.generate_codes(session, amount, count, payload.get("batch"))
    return {"codes": codes, "amount_credits": amount, "count": len(codes)}


@router.get("/redemption")
async def list_redemption(session: AsyncSession = Depends(get_session), limit: int = 200):
    rows = (
        await session.execute(select(RedemptionCode).order_by(RedemptionCode.id.desc()).limit(limit))
    ).scalars().all()
    return {"codes": [
        {"id": r.id, "code": r.code, "amount_credits": r.amount_credits, "batch": r.batch,
         "status": r.status, "used_by": r.used_by, "used_at": r.used_at}
        for r in rows
    ]}


@router.post("/redemption/void")
async def void_redemption(session: AsyncSession = Depends(get_session), payload: dict = Body(default={})):
    """作废未使用的兑换码。支持按 id 或按 batch 批量作废。返回作废数量。"""
    rid = payload.get("id")
    batch = payload.get("batch")
    if rid is None and not batch:
        raise HTTPException(status_code=400, detail="id or batch required")
    q = select(RedemptionCode).where(RedemptionCode.status == 1)
    if rid is not None:
        q = q.where(RedemptionCode.id == int(rid))
    if batch:
        q = q.where(RedemptionCode.batch == batch)
    rows = (await session.execute(q)).scalars().all()
    for r in rows:
        r.status = 2  # 作废
    await session.commit()
    return {"voided": len(rows)}


@router.get("/redemption/export")
async def export_redemption(session: AsyncSession = Depends(get_session),
                            batch: str | None = None, only_unused: int = 1):
    """导出兑换码为 CSV 文本（code,amount_credits,batch,status）。"""
    q = select(RedemptionCode).order_by(RedemptionCode.id.desc())
    if batch:
        q = q.where(RedemptionCode.batch == batch)
    if only_unused:
        q = q.where(RedemptionCode.status == 1)
    rows = (await session.execute(q)).scalars().all()
    lines = ["code,amount_credits,batch,status"]
    for r in rows:
        lines.append(f"{r.code},{r.amount_credits},{r.batch or ''},{r.status}")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("\n".join(lines), media_type="text/csv")


# ---------------- request logs (v2.2) ----------------
@router.get("/logs")
async def logs(session: AsyncSession = Depends(get_session),
               services: AppServices = Depends(get_services),
               limit: int = 50, offset: int = 0,
               user_id: int | None = None, token_name: str | None = None,
               model: str | None = None, channel: str | None = None,
               status: int | None = None, only_errors: int = 0,
               start: float | None = None, end: float | None = None):
    limit = max(1, min(limit, 200))
    return await services.usage.query_logs(
        session, limit=limit, offset=max(0, offset), user_id=user_id,
        token_name=token_name, model=model, channel=channel, status=status,
        only_errors=bool(only_errors), start=start, end=end,
    )


@router.get("/logs/stats")
async def logs_stats(session: AsyncSession = Depends(get_session),
                     services: AppServices = Depends(get_services), days: int = 7):
    return await services.usage.stats(session, days=max(1, min(days, 90)))


# ---------------- orders manual (v2.2) ----------------
@router.post("/orders/{order_no}/mark-paid")
async def mark_order_paid(order_no: str, request: Request,
                          session: AsyncSession = Depends(get_session),
                          services: AppServices = Depends(get_services)):
    """手动补单：将订单标记为已支付并幂等入账。"""
    ok = await services.orders.mark_paid(session, order_no)
    if not ok:
        raise HTTPException(status_code=404, detail="order not found")
    await services.audit.record(
        session, actor="admin", action="order.mark_paid", target=order_no,
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "order_no": order_no}


# ---------------- analytics & batch (v2.4) ----------------
@router.get("/analytics/overview")
async def analytics_overview(session: AsyncSession = Depends(get_session),
                             services: AppServices = Depends(get_services), days: int = 30):
    days = max(1, min(days, 365))
    revenue = await services.billing.revenue(session, days=days)
    usage_stats = await services.usage.stats(session, days=min(days, 90))
    return {"revenue": revenue, "usage": usage_stats}


@router.get("/analytics/ranking")
async def analytics_ranking(session: AsyncSession = Depends(get_session),
                            services: AppServices = Depends(get_services),
                            by: str = "model", days: int = 30, limit: int = 10):
    if by not in ("model", "user", "channel"):
        raise HTTPException(status_code=400, detail="by must be model|user|channel")
    limit = max(1, min(limit, 100))
    return {"by": by, "days": days,
            "ranking": await services.usage.ranking(session, by=by, days=days, limit=limit)}


@router.get("/analytics/timeseries")
async def analytics_timeseries(session: AsyncSession = Depends(get_session),
                               services: AppServices = Depends(get_services),
                               days: int = 14, metric: str = "requests"):
    if metric not in ("requests", "cost", "tokens"):
        raise HTTPException(status_code=400, detail="metric must be requests|cost|tokens")
    days = max(1, min(days, 90))
    return {"metric": metric, "days": days,
            "series": await services.usage.timeseries(session, days=days, metric=metric)}


@router.get("/alerts")
async def alerts(session: AsyncSession = Depends(get_session),
                 services: AppServices = Depends(get_services), min_balance: int = 0):
    # 熔断渠道
    circuit = (await session.execute(select(Channel).where(Channel.status == 2))).scalars().all()
    circuit_open = [{"id": c.id, "name": c.name, "fail_count": c.fail_count} for c in circuit]
    # 低余额用户（启用中、余额 <= 阈值）
    low = []
    if min_balance > 0:
        rows = (await session.execute(
            select(User).where(User.status == 1, User.balance <= min_balance).limit(50)
        )).scalars().all()
        low = [{"id": u.id, "username": u.username, "balance": u.balance} for u in rows]
    return {"circuit_open": circuit_open, "low_balance": low}


@router.post("/tokens/batch")
async def tokens_batch(request: Request, session: AsyncSession = Depends(get_session),
                       services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    ids = payload.get("ids") or []
    action = payload.get("action")
    if not isinstance(ids, list) or not ids or action not in ("enable", "disable", "delete"):
        raise HTTPException(status_code=400, detail="ids[] and action(enable|disable|delete) required")
    ids = [int(i) for i in ids][:500]
    rows = (await session.execute(select(Token).where(Token.id.in_(ids)))).scalars().all()
    n = 0
    for t in rows:
        if action == "delete":
            await session.delete(t)
        else:
            t.enabled = 1 if action == "enable" else 0
        n += 1
    await session.commit()
    await services.audit.record(session, actor="admin", action=f"batch.token.{action}",
                                detail={"count": n, "ids": ids},
                                ip=request.client.host if request.client else None)
    return {"affected": n, "action": action}


@router.post("/users/batch-topup")
async def users_batch_topup(request: Request, session: AsyncSession = Depends(get_session),
                            services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    user_ids = payload.get("user_ids") or []
    amount = int(payload.get("amount") or 0)
    if not user_ids or amount == 0:
        raise HTTPException(status_code=400, detail="user_ids[] and non-zero amount required")
    n = 0
    for uid in [int(i) for i in user_ids][:500]:
        u = await services.billing.topup(session, uid, amount, ref="admin-batch", type_="adjust")
        if u is not None:
            n += 1
    await services.audit.record(session, actor="admin", action="batch.user.topup",
                                detail={"count": n, "amount": amount},
                                ip=request.client.host if request.client else None)
    return {"affected": n, "amount": amount}


@router.post("/redemption/grant")
async def redemption_grant(request: Request, session: AsyncSession = Depends(get_session),
                           services: AppServices = Depends(get_services), payload: dict = Body(default={})):
    """直接给指定用户充值（记流水），用于线下/客服补偿场景。"""
    uid = payload.get("user_id")
    amount = int(payload.get("amount") or 0)
    if not uid or amount <= 0:
        raise HTTPException(status_code=400, detail="user_id and positive amount required")
    u = await services.billing.topup(session, int(uid), amount,
                                     ref=f"grant:{payload.get('note', '')}", type_="topup")
    if u is None:
        raise HTTPException(status_code=404, detail="user not found")
    await services.audit.record(session, actor="admin", action="user.grant", target=str(uid),
                                detail={"amount": amount},
                                ip=request.client.host if request.client else None)
    return _user_dict(u)


# ---------------- serializers ----------------
def _user_dict(u: User) -> dict:
    return {"id": u.id, "username": u.username, "email": u.email, "role": u.role,
            "group": u.group, "balance": u.balance, "frozen": u.frozen, "status": u.status}


def _token_dict(t: Token, reveal: bool = False) -> dict:
    return {"id": t.id, "user_id": t.user_id, "key": t.key, "name": t.name,
            "enabled": t.enabled, "quota_tokens": t.quota_tokens, "used_tokens": t.used_tokens,
            "rpm_limit": t.rpm_limit, "allowed_models": t.allowed_models,
            "allowed_groups": t.allowed_groups, "expires_at": t.expires_at, "note": t.note}


def _channel_dict(c: Channel) -> dict:
    return {"id": c.id, "name": c.name, "type": c.type, "base_url": c.base_url,
            "models": json.loads(c.models or "[]"), "model_map": json.loads(c.model_map or "{}"),
            "headers": json.loads(c.headers or "{}"), "group": c.group, "weight": c.weight,
            "priority": c.priority, "status": c.status, "fail_count": c.fail_count,
            "key_count": len(json.loads(c.api_keys or "[]"))}


def _pricing_dict(p: ModelPricing) -> dict:
    return {"id": p.id, "model": p.model, "group": p.group, "input_price": p.input_price,
            "output_price": p.output_price, "cache_price": p.cache_price,
            "multiplier": p.multiplier, "enabled": p.enabled}


def _order_dict(o: Order) -> dict:
    return {"id": o.id, "order_no": o.order_no, "user_id": o.user_id,
            "amount_credits": o.amount_credits, "amount_money": o.amount_money,
            "currency": o.currency, "method": o.method, "status": o.status,
            "provider": o.provider, "provider_order": o.provider_order,
            "created_at": o.created_at, "paid_at": o.paid_at, "expires_at": o.expires_at}


# ---------------- helpers ----------------
def _expires(payload: dict):
    if payload.get("expires_at") is not None:
        return payload["expires_at"]
    days = payload.get("expires_in_days")
    if days:
        return time.time() + float(days) * 86400
    return None


def _models_str(val):
    if isinstance(val, list):
        return ",".join(str(m).strip() for m in val if str(m).strip()) or None
    if isinstance(val, str):
        return val.strip() or None
    return None
