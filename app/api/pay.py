"""充值与支付端点。

- POST /pay/orders           创建充值订单（需令牌/用户身份）
- GET  /pay/orders/{no}      查询订单状态（主动触发一次对账）
- POST /pay/redeem           兑换码充值
- POST /pay/notify/{provider} 支付异步回调（无鉴权，靠验签）

身份：复用 get_principal（token 角色带 user_id）。回调无身份，靠 provider 验签。
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.state import AppServices
from ..db.base import get_session
from ..db.models import Order
from ..domain.orders import OrderError
from .deps import get_services, get_user_id

router = APIRouter(prefix="/pay")


@router.get("/methods")
async def payment_methods(services: AppServices = Depends(get_services)):
    """列出已启用的支付方式。"""
    return {"methods": sorted(services.payments.keys())}


@router.post("/orders")
async def create_order(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
    user_id: int = Depends(get_user_id),
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")
    method = (payload.get("method") or "").strip()
    amount_money = int(payload.get("amount_money") or 0)
    if not method:
        raise HTTPException(status_code=400, detail="missing 'method'")
    try:
        order = await services.orders.create(session, user_id, method, amount_money)
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _order_dict(order)


@router.get("/orders/{order_no}")
async def get_order(
    order_no: str,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
    user_id: int = Depends(get_user_id),
):
    order = (
        await session.execute(select(Order).where(Order.order_no == order_no))
    ).scalar_one_or_none()
    if order is None or order.user_id != user_id:
        raise HTTPException(status_code=404, detail="order not found")
    # 主动对账一次（pending 且未过期）
    if order.status == "pending":
        try:
            await services.orders.reconcile_one(session, order)
            await session.refresh(order)
        except Exception:
            pass
    return _order_dict(order)


@router.post("/redeem")
async def redeem(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
    user_id: int = Depends(get_user_id),
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")
    code = (payload.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="missing 'code'")
    try:
        credited = await services.orders.redeem(session, user_id, code)
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"credited": credited}


@router.post("/notify/{provider}")
@router.get("/notify/{provider}")
async def payment_notify(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
):
    """支付异步回调：验签 → 幂等入账。返回 provider 期望的确认字符串。"""
    prov = services.payments.get(provider)
    if prov is None:
        raise HTTPException(status_code=404, detail="provider not enabled")
    body = await request.body()
    form = {}
    if request.method == "GET":
        form = dict(request.query_params)
    else:
        ctype = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in ctype or "multipart" in ctype:
            form = dict(await request.form())
        elif "application/json" in ctype:
            try:
                import json
                form = json.loads(body or b"{}")
            except Exception:
                form = {}
        else:
            form = dict(request.query_params)

    result = prov.verify_callback(dict(request.headers), body, form)
    if not result.ok or not result.order_no:
        raise HTTPException(status_code=400, detail="invalid callback")
    await services.orders.mark_paid(session, result.order_no, result.provider_order)
    # 易支付要求回 "success"
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("success")


def _order_dict(o: Order) -> dict:
    return {
        "order_no": o.order_no, "status": o.status, "method": o.method,
        "amount_money": o.amount_money, "amount_credits": o.amount_credits,
        "currency": o.currency, "pay_url": o.pay_url, "pay_address": o.pay_address,
        "provider_order": o.provider_order, "expires_at": o.expires_at,
        "created_at": o.created_at, "paid_at": o.paid_at,
    }
