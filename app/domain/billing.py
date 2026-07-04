"""计费服务：余额、预扣冻结、结算、流水记账。

预扣式（解决"事后扣费"超额漏洞）：
  1. 请求前 freeze(estimate)：balance -= est, frozen += est（不足则拒绝）
  2. 请求后 settle(est, actual)：解冻 est，实扣 actual，差额退回
所有余额变动都写 billing_ledger，保证 balance == Σ ledger.amount。
"""
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import BillingLedger, User


class InsufficientBalance(Exception):
    pass


class BillingService:
    async def get_user(self, session: AsyncSession, user_id: int) -> User | None:
        return (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

    async def revenue(self, session: AsyncSession, days: int = 30) -> dict:
        """收入报表：按区间聚合 billing_ledger 各类型金额。

        topup: 用户充值入账；adjust: 管理员调整（可正可负）；
        consume: 消费(负值)；refund: 退款。净收入 = topup + adjust(正) - refund。
        """
        start = time.time() - max(days, 1) * 86400
        rows = (
            await session.execute(
                select(BillingLedger.type,
                       func.coalesce(func.sum(BillingLedger.amount), 0).label("amount"),
                       func.count().label("count"))
                .where(BillingLedger.ts >= start)
                .group_by(BillingLedger.type)
            )
        ).all()
        by_type = {r.type: {"amount": int(r.amount or 0), "count": r.count} for r in rows}
        topup = by_type.get("topup", {}).get("amount", 0)
        adjust = by_type.get("adjust", {}).get("amount", 0)
        consume = -by_type.get("consume", {}).get("amount", 0)  # 转正表示消费额
        refund = -by_type.get("refund", {}).get("amount", 0)
        return {
            "days": days,
            "topup": topup, "adjust": adjust, "consume": consume, "refund": refund,
            "net_income": topup + max(adjust, 0) - refund,
            "by_type": by_type,
        }


    async def freeze(self, session: AsyncSession, user_id: int, amount: int) -> None:
        """预扣冻结。amount<=0 直接放行（如无定价）。"""
        if amount <= 0:
            return
        user = await self.get_user(session, user_id)
        if user is None:
            raise InsufficientBalance("user not found")
        if user.balance < amount:
            raise InsufficientBalance(
                f"insufficient balance: need {amount}, have {user.balance}"
            )
        user.balance -= amount
        user.frozen += amount
        await session.commit()

    async def settle(
        self, session: AsyncSession, user_id: int, frozen_amount: int, actual_cost: int, ref: str
    ) -> None:
        """结算：释放冻结，按实际扣费，差额退回余额，记流水。"""
        user = await self.get_user(session, user_id)
        if user is None:
            return
        # 先把冻结的金额全部释放回余额
        release = min(frozen_amount, user.frozen)
        user.frozen -= release
        user.balance += release
        # 再按实际成本扣除
        actual = min(actual_cost, user.balance) if actual_cost > 0 else 0
        if actual > 0:
            user.balance -= actual
            session.add(
                BillingLedger(
                    user_id=user_id, type="consume", amount=-actual,
                    balance_after=user.balance, ref=ref,
                )
            )
        await session.commit()

    async def topup(
        self, session: AsyncSession, user_id: int, amount: int, ref: str, type_: str = "topup"
    ) -> User | None:
        user = await self.get_user(session, user_id)
        if user is None:
            return None
        user.balance += amount
        session.add(
            BillingLedger(
                user_id=user_id, type=type_, amount=amount,
                balance_after=user.balance, ref=ref,
            )
        )
        await session.commit()
        return user
