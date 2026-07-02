"""网关端点（OpenAI 兼容 + Claude 原生）：
- /v1/chat/completions   聊天（流式/非流式）
- /v1/embeddings         向量
- /v1/images/generations 文生图
- /v1/messages           Anthropic 原生入口（转成统一表示后复用同一条链路）
- /v1/models, /v1/me
"""
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
    payload = await _json(request)
    return await _prepare_and_forward(payload, "chat", session, services, principal)


@router.post("/embeddings")
async def embeddings(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
    principal: Principal = Depends(get_principal),
):
    payload = await _json(request)
    return await _prepare_and_forward(payload, "embeddings", session, services, principal)


@router.post("/images/generations")
async def images_generations(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
    principal: Principal = Depends(get_principal),
):
    payload = await _json(request)
    return await _prepare_and_forward(payload, "images", session, services, principal)


@router.post("/messages")
async def anthropic_messages(
    request: Request,
    session: AsyncSession = Depends(get_session),
    services: AppServices = Depends(get_services),
    principal: Principal = Depends(get_principal),
):
    """Anthropic 原生 Messages 入口：把 Anthropic 请求转成统一表示后复用同一链路。

    注：响应目前以 OpenAI 格式返回（统一表示）。若上游本身是 Anthropic 渠道，
    等价于原生直连；跨协议（如底层是 OpenAI 上游）也可用。
    """
    payload = await _json(request)
    unified = _anthropic_to_unified(payload)
    return await _prepare_and_forward(unified, "chat", session, services, principal)


# ---------------- 共享链路 ----------------
async def _prepare_and_forward(
    payload: dict, endpoint: str, session: AsyncSession,
    services: AppServices, principal: Principal,
):
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

    # 计费预扣（仅有 user_id 且有定价时）
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
        pricing_row=pricing_row, frozen_amount=frozen, endpoint=endpoint,
        health=services.health,
    )
    return await forward(ctx, attempts, payload, bool(payload.get("stream")))


async def _json(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")


def _anthropic_to_unified(payload: dict) -> dict:
    """Anthropic Messages 请求 → OpenAI Chat 统一表示。"""
    messages = []
    system = payload.get("system")
    if isinstance(system, str) and system:
        messages.append({"role": "system", "content": system})
    elif isinstance(system, list):
        text = "\n\n".join(p.get("text", "") for p in system if isinstance(p, dict))
        if text:
            messages.append({"role": "system", "content": text})
    for m in payload.get("messages") or []:
        content = m.get("content")
        if isinstance(content, list):
            texts = [p.get("text", "") for p in content
                     if isinstance(p, dict) and p.get("type") == "text"]
            content = "\n".join(t for t in texts if t)
        messages.append({"role": m.get("role", "user"), "content": content})
    unified = {"model": payload.get("model"), "messages": messages}
    if payload.get("max_tokens") is not None:
        unified["max_tokens"] = payload["max_tokens"]
    if payload.get("temperature") is not None:
        unified["temperature"] = payload["temperature"]
    if payload.get("stream"):
        unified["stream"] = True
    return unified


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
    # embeddings 用 input 字段
    inp = payload.get("input")
    if isinstance(inp, str):
        chars += len(inp)
    elif isinstance(inp, list):
        chars += sum(len(x) for x in inp if isinstance(x, str))
    return max(chars // 4, 1)
