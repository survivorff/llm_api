"""网关端点（OpenAI 兼容）：/v1/chat/completions, /v1/models, /v1/me。"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.state import AppServices
from ..db.base import get_session
from ..domain.auth import Principal
from ..domain.billing import InsufficientBalance
from ..domain.proxy import ForwardContext, forward
from ..domain.routing import NoChannelError
from .deps import get_principal, get_services

router = APIRouter(prefix="/v1")


@router.get("/models")
async def list_models(
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
    principal: Principal = Depends(get_principal),
):
    data = [
        {"id": m, "object": "model", "owned_by": cn}
        for m, cn in await services.router.list_models(session)
    ]
    return {"object": "list", "data": data}


@router.get("/me")
async def whoami(principal: Principal = Depends(get_principal)):
    if principal.kind != "token":
        return {"name": principal.name, "role": principal.kind, "unlimited": True}
    quota = principal.quota_tokens
    used = principal.used_tokens or 0
    return {
        "name": principal.name, "role": "token",
        "used_tokens": used, "quota_tokens": quota,
        "remaining_tokens": None if quota is None else max(quota - used, 0),
        "rpm_limit": principal.rpm_limit, "expires_at": principal.expires_at,
        "allowed_models": principal.allowed_models,
        "balance": principal.balance,
    }


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
    principal: Principal = Depends(get_principal),
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")
    model = payload.get("model")
    if not model:
        raise HTTPException(status_code=400, detail="missing 'model'")

    # 模型白名单
    if principal.allowed_models is not None and model not in principal.allowed_models:
        raise HTTPException(status_code=403, detail=f"model '{model}' not allowed for this token")

    # 限速（分布式）
    if principal.rpm_limit and principal.token_id:
        if not await services.limiter.allow(f"tok:{principal.token_id}", principal.rpm_limit):
            raise HTTPException(status_code=429, detail="rate limit exceeded (RPM)")

    # 路由
    try:
        attempts = await services.router.resolve(session, model, principal.allowed_groups)
    except NoChannelError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 计费预扣（仅 token 角色且有 user_id）
    pricing_row = None
    frozen = 0
    if principal.user_id:
        pricing_row = await services.pricing.get_pricing(session, model, principal.group)
        if pricing_row:
            prompt_est = _estimate_prompt_tokens(payload)
            max_completion = payload.get("max_tokens") or get_settings().default_prefreeze_tokens
            frozen = services.pricing.estimate_max_cost(pricing_row, prompt_est, max_completion)
            try:
                await services.billing.freeze(session, principal.user_id, frozen)
            except InsufficientBalance as e:
                raise HTTPException(status_code=402, detail=str(e))

    ctx = ForwardContext(
        http=services.http, router=services.router, billing=services.billing,
        usage=services.usage, pricing=services.pricing, principal=principal,
        pricing_row=pricing_row, frozen_amount=frozen,
    )
    return await forward(ctx, attempts, payload, bool(payload.get("stream")))


def _estimate_prompt_tokens(payload: dict) -> int:
    """粗略估算 prompt token 数（4 字符≈1 token），仅用于预扣冻结。"""
    chars = 0
    for m in payload.get("messages") or []:
        c = m.get("content")
        if isinstance(c, str):
            chars += len(c)
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    chars += len(part["text"])
    return max(chars // 4, 1)
