"""定价服务：根据模型 + 用户分组计算费用（credits）。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ModelPricing


class PricingService:
    async def get_pricing(self, session: AsyncSession, model: str, group: str) -> ModelPricing | None:
        # 先找分组专属价，回退 default 分组
        for g in (group, "default"):
            row = (
                await session.execute(
                    select(ModelPricing).where(
                        ModelPricing.model == model,
                        ModelPricing.group == g,
                        ModelPricing.enabled == 1,
                    )
                )
            ).scalar_one_or_none()
            if row:
                return row
        return None

    def compute_cost(
        self,
        pricing: ModelPricing | None,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int = 0,
    ) -> int:
        """返回 credits（整数）。无定价则计 0（不扣费，仅记录）。"""
        if pricing is None:
            return 0
        billable_prompt = max(prompt_tokens - cached_tokens, 0)
        cost = (
            billable_prompt / 1000 * pricing.input_price
            + completion_tokens / 1000 * pricing.output_price
        )
        if cached_tokens and pricing.cache_price:
            cost += cached_tokens / 1000 * pricing.cache_price
        cost *= pricing.multiplier
        return int(round(cost))

    def estimate_max_cost(
        self, pricing: ModelPricing | None, prompt_tokens: int, max_completion: int
    ) -> int:
        """预扣估算：按最坏情况（全部按 output 价）冻结。"""
        if pricing is None:
            return 0
        cost = (
            prompt_tokens / 1000 * pricing.input_price
            + max_completion / 1000 * pricing.output_price
        ) * pricing.multiplier
        return int(round(cost))
