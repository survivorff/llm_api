"""计费服务：余额、预扣冻结、结算、流水记账。

预扣式（解决"事后扣费"超额漏洞）：
  1. 请求前 freeze(estimate)：balance -= est, frozen += est（不足则拒绝）
  2. 请求后 settle(est, actual)：解冻 est，实扣 actual，差额退回
所有余额变动都写 billing_ledger，保证 balance == Σ ledger.amount。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import BillingLedger, User


class InsufficientBalance(Exception):
    pass


class BillingService:
    async def get_user(self, session: AsyncSession, user_id: int) -> User | None:
        return (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

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
