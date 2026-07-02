"""充值订单服务：创建订单、处理支付成功（幂等入账）、兑换码、对账查询。

金额换算：
  amount_credits = amount_money 按各方式的汇率换算
  - 法币（epay/wechat/alipay）：amount_money 单位「分」，credits = 元 * credits_per_usd / usd_cny_rate
  - 加密（crypto）：amount_money 单位「微 USDT」，credits = USDT * credits_per_usd（USDT≈USD）

幂等：订单从 pending → paid 只发生一次，入账写 billing_ledger。
"""
import json
import random
import secrets
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Order, RedemptionCode
from ..payments import PaymentRequest
from .billing import BillingService


class OrderError(Exception):
    pass


def _order_no() -> str:
    return time.strftime("%Y%m%d%H%M%S") + secrets.token_hex(4)


class OrderService:
    def __init__(self, billing: BillingService, providers: dict, settings):
        self.billing = billing
        self.providers = providers
        self.settings = settings

    # ---------------- 汇率换算 ----------------
    def _credits_for(self, method: str, amount_money: int) -> int:
        cpu = self.settings.credits_per_usd
        if method == "crypto":
            # amount_money 微 USDT → USDT → credits（USDT≈USD）
            return int(round(amount_money / 1_000_000 * cpu))
        # 法币：分 → 元 → USD → credits
        yuan = amount_money / 100
        usd = yuan / max(self.settings.usd_cny_rate, 0.01)
        return int(round(usd * cpu))

    # ---------------- 创建订单 ----------------
    async def create(
        self, session: AsyncSession, user_id: int, method: str,
        amount_money: int, channel: str | None = None,
    ) -> Order:
        if amount_money <= 0:
            raise OrderError("amount must be positive")
        provider = self.providers.get(method) or self.providers.get(channel or "")
        # crypto/epay 统一映射
        pname = method
        if method in ("wechat", "alipay"):
            provider = self.providers.get(method) or self.providers.get("epay")
            pname = "epay"
        if provider is None:
            raise OrderError(f"payment method '{method}' not enabled")

        credits = self._credits_for("crypto" if method == "crypto" else "fiat", amount_money)
        order = Order(
            order_no=_order_no(), user_id=user_id, amount_credits=credits,
            amount_money=amount_money, currency="USDT" if method == "crypto" else "CNY",
            method=method, status="pending", provider=pname,
            created_at=time.time(), expires_at=time.time() + self.settings.order_ttl_seconds,
        )

        # crypto：分配唯一金额尾数用于对账（微 USDT 上加 0~999 随机）
        req_extra = {}
        if method == "crypto":
            unique = amount_money + random.randint(1, 999)
            order.amount_money = unique
            order.provider_order = str(unique)  # 期望精确到账金额
            req_extra = {}
        else:
            req_extra = {"channel": "wxpay" if method == "wechat" else "alipay"}

        req = PaymentRequest(
            order_no=order.order_no, amount_money=order.amount_money,
            currency=order.currency, subject=f"topup {credits} credits", extra=req_extra,
        )
        result = await provider.create_payment(req)
        if not result.ok:
            raise OrderError(result.error or "create payment failed")
        order.pay_url = result.pay_url
        order.pay_address = result.pay_address
        if result.provider_order:
            order.provider_order = result.provider_order
        order.extra = json.dumps(result.extra or {}, ensure_ascii=False)

        session.add(order)
        await session.commit()
        return order

    # ---------------- 标记支付成功（幂等） ----------------
    async def mark_paid(self, session: AsyncSession, order_no: str, provider_order: str | None = None) -> bool:
        order = (
            await session.execute(select(Order).where(Order.order_no == order_no))
        ).scalar_one_or_none()
        if order is None:
            return False
        if order.status == "paid":
            return True  # 幂等：已入账
        order.status = "paid"
        order.paid_at = time.time()
        if provider_order:
            order.provider_order = provider_order
        await session.commit()
        # 入账
        await self.billing.topup(
            session, order.user_id, order.amount_credits,
            ref=f"order={order.order_no};method={order.method}", type_="topup",
        )
        return True

    # ---------------- 对账：主动查询 provider ----------------
    async def reconcile_one(self, session: AsyncSession, order: Order) -> bool:
        provider = self.providers.get(order.provider) or self.providers.get(order.method)
        if provider is None:
            return False
        paid = await provider.query_status(order.order_no, order.provider_order)
        if paid:
            return await self.mark_paid(session, order.order_no)
        return False

    async def expire_stale(self, session: AsyncSession) -> int:
        now = time.time()
        rows = (
            await session.execute(
                select(Order).where(Order.status == "pending", Order.expires_at < now)
            )
        ).scalars().all()
        for o in rows:
            o.status = "expired"
        if rows:
            await session.commit()
        return len(rows)

    # ---------------- 兑换码 ----------------
    async def generate_codes(
        self, session: AsyncSession, amount_credits: int, count: int, batch: str | None = None
    ) -> list[str]:
        codes = []
        for _ in range(count):
            code = secrets.token_urlsafe(12)
            session.add(RedemptionCode(code=code, amount_credits=amount_credits, batch=batch))
            codes.append(code)
        await session.commit()
        return codes

    async def redeem(self, session: AsyncSession, user_id: int, code: str) -> int:
        rc = (
            await session.execute(select(RedemptionCode).where(RedemptionCode.code == code))
        ).scalar_one_or_none()
        if rc is None:
            raise OrderError("invalid code")
        if rc.status != 1:
            raise OrderError("code already used or void")
        rc.status = 0
        rc.used_by = user_id
        rc.used_at = time.time()
        await session.commit()
        await self.billing.topup(
            session, user_id, rc.amount_credits, ref=f"redeem={code}", type_="topup"
        )
        return rc.amount_credits
