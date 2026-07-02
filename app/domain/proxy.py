"""转发层：OpenAI 兼容请求 → 上游，支持流式/非流式 + 故障转移 + 预扣结算 + 用量记账。

计费流程：
  freeze(est) 已在调用方（api 层）完成 → 这里拿到 frozen_amount
  转发结束后按实际 usage 计算 cost，调用 settle 释放冻结并实扣。
"""
import json
import time

import httpx
from fastapi.responses import JSONResponse, StreamingResponse

from ..db.base import get_sessionmaker

RETRYABLE = {429, 500, 502, 503, 504, 529}


class ForwardContext:
    """封装一次转发所需的依赖与计费上下文。"""

    def __init__(self, http, router, billing, usage, pricing, principal,
                 pricing_row, frozen_amount):
        self.http = http
        self.router = router
        self.billing = billing
        self.usage = usage
        self.pricing = pricing
        self.principal = principal
        self.pricing_row = pricing_row
        self.frozen_amount = frozen_amount


async def _finalize(ctx: ForwardContext, *, model, upstream_model, channel, status,
                    latency_ms, usage_obj, stream, error):
    """写用量日志 + 结算计费。用独立 session，避免与请求 session 冲突。"""
    prompt = (usage_obj or {}).get("prompt_tokens")
    completion = (usage_obj or {}).get("completion_tokens")
    total = (usage_obj or {}).get("total_tokens")
    cached = None
    details = (usage_obj or {}).get("prompt_tokens_details") or {}
    if isinstance(details, dict):
        cached = details.get("cached_tokens")

    cost = 0
    if status < 400 and total:
        cost = ctx.pricing.compute_cost(
            ctx.pricing_row, prompt or 0, completion or 0, cached or 0
        )

    async with get_sessionmaker()() as session:
        await ctx.usage.log(
            session,
            ts=time.time(), user_id=ctx.principal.user_id, token_id=ctx.principal.token_id,
            token_name=ctx.principal.name, channel=channel, model=model,
            upstream_model=upstream_model, status=status, latency_ms=latency_ms,
            prompt_tokens=prompt, completion_tokens=completion, cached_tokens=cached,
            total_tokens=total, cost=cost, stream=1 if stream else 0, error=error,
        )
        if status < 400 and total:
            await ctx.usage.add_token_usage(session, ctx.principal.token_id, total)
        # 结算：释放冻结，实扣 cost
        if ctx.principal.user_id and ctx.frozen_amount >= 0:
            ref = f"model={model};channel={channel}"
            await ctx.billing.settle(
                session, ctx.principal.user_id, ctx.frozen_amount, cost, ref
            )


async def forward(ctx: ForwardContext, attempts, payload, stream):
    client: httpx.AsyncClient = ctx.http
    model = payload.get("model")
    last_error, last_status = None, None

    for att in attempts:
        body = dict(payload)
        body["model"] = att.upstream_model
        headers = {"Authorization": f"Bearer {att.api_key}", "Content-Type": "application/json"}
        headers.update(att.headers)
        started = time.time()

        if stream:
            if "stream_options" not in body:
                body["stream_options"] = {"include_usage": True}
            req = client.build_request("POST", att.url, json=body, headers=headers, timeout=None)
            try:
                resp = await client.send(req, stream=True)
            except httpx.RequestError as e:
                last_error = str(e)
                continue
            if resp.status_code in RETRYABLE:
                await resp.aread()
                await resp.aclose()
                last_status = resp.status_code
                continue
            return StreamingResponse(
                _stream_iter(ctx, resp, model, att, started),
                status_code=resp.status_code,
                media_type="text/event-stream",
            )

        # 非流式
        try:
            resp = await client.post(att.url, json=body, headers=headers, timeout=300.0)
        except httpx.RequestError as e:
            last_error = str(e)
            continue
        if resp.status_code in RETRYABLE:
            last_status = resp.status_code
            last_error = resp.text[:500]
            continue

        latency = int((time.time() - started) * 1000)
        data, usage_obj = None, {}
        if resp.headers.get("content-type", "").startswith("application/json"):
            try:
                data = resp.json()
                usage_obj = data.get("usage") or {}
            except Exception:
                data = None
        err = None
        if resp.status_code >= 400:
            err = (json.dumps(data) if data is not None else resp.text)[:500]

        await _finalize(ctx, model=model, upstream_model=att.upstream_model, channel=att.channel,
                        status=resp.status_code, latency_ms=latency, usage_obj=usage_obj,
                        stream=False, error=err)
        if data is not None:
            return JSONResponse(status_code=resp.status_code, content=data)
        return JSONResponse(status_code=resp.status_code, content={"raw": resp.text})

    # 全部失败：释放冻结（不扣费）
    await _finalize(ctx, model=model, upstream_model=model, channel="none",
                    status=last_status or 502, latency_ms=0, usage_obj={},
                    stream=stream, error=last_error or "all upstreams failed")
    return JSONResponse(
        status_code=502,
        content={"error": {"message": last_error or "all upstreams failed",
                           "upstream_status": last_status}},
    )


async def _stream_iter(ctx: ForwardContext, resp, model, att, started):
    pending = ""
    captured = None
    try:
        async for chunk in resp.aiter_raw():
            yield chunk
            pending += chunk.decode("utf-8", "ignore")
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                u = obj.get("usage")
                if u and u.get("total_tokens") is not None:
                    captured = u
    finally:
        latency = int((time.time() - started) * 1000)
        status = resp.status_code
        await resp.aclose()
        await _finalize(ctx, model=model, upstream_model=att.upstream_model, channel=att.channel,
                        status=status, latency_ms=latency, usage_obj=captured or {},
                        stream=True, error=None)
