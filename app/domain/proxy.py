"""转发层：统一表示 → 上游（经适配器），支持流式/非流式 + 故障转移 + 预扣结算 + 用量记账。

计费流程：
  freeze(est) 已在调用方（api 层）完成 → 这里拿到 frozen_amount
  转发结束后按实际 usage 计算 cost，调用 settle 释放冻结并实扣。

适配器：按渠道 type 选择（openai 透传 / claude / gemini 互转），
转发层只跟「OpenAI Chat 统一表示」打交道。
"""
import json
import time

import httpx
from fastapi.responses import JSONResponse, StreamingResponse

from ..adapters import get_adapter
from ..core import metrics
from ..db.base import get_sessionmaker

RETRYABLE = {429, 500, 502, 503, 504, 529}


class ForwardContext:
    """封装一次转发所需的依赖与计费上下文。"""

    def __init__(self, http, router, billing, usage, pricing, principal,
                 pricing_row, frozen_amount, endpoint="chat", health=None):
        self.http = http
        self.router = router
        self.billing = billing
        self.usage = usage
        self.pricing = pricing
        self.principal = principal
        self.pricing_row = pricing_row
        self.frozen_amount = frozen_amount
        self.endpoint = endpoint
        self.health = health  # 渠道健康巡检服务（可选）


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

    # Prometheus 指标
    outcome = "ok" if status < 400 else "error"
    metrics.inc_counter("llm_api_requests_total", endpoint=ctx.endpoint,
                        model=model or "unknown", status=status, outcome=outcome)
    if status >= 400:
        metrics.inc_counter("llm_api_request_errors_total", endpoint=ctx.endpoint,
                            status=status)
    if total:
        metrics.inc_counter("llm_api_tokens_total", float(total), model=model or "unknown")
    if latency_ms:
        metrics.observe_latency("llm_api_request_duration_seconds", latency_ms / 1000.0,
                               endpoint=ctx.endpoint)

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
    endpoint = ctx.endpoint
    last_error, last_status = None, None

    for att in attempts:
        adapter = get_adapter(att.type)
        url, headers, body = adapter.build_request(
            att.base_url, att.upstream_model, att.api_key, payload, att.headers, endpoint
        )
        started = time.time()

        if stream:
            req = client.build_request("POST", url, json=body, headers=headers, timeout=None)
            try:
                resp = await client.send(req, stream=True)
            except httpx.RequestError as e:
                last_error = str(e)
                await _mark(ctx, att, False)
                continue
            if resp.status_code in RETRYABLE:
                await resp.aread()
                await resp.aclose()
                last_status = resp.status_code
                await _mark(ctx, att, False)
                continue
            if resp.status_code >= 400:
                # 非重试类错误：读取错误体直接返回
                await resp.aread()
                await _finalize(ctx, model=model, upstream_model=att.upstream_model,
                                channel=att.channel, status=resp.status_code, latency_ms=0,
                                usage_obj={}, stream=True, error=resp.text[:500])
                await resp.aclose()
                return JSONResponse(status_code=resp.status_code,
                                    content=_err_body(resp.text, resp.status_code))
            await _mark(ctx, att, True)
            return StreamingResponse(
                _stream_iter(ctx, adapter, resp, model, att, started),
                status_code=resp.status_code,
                media_type="text/event-stream",
            )

        # 非流式
        try:
            resp = await client.post(url, json=body, headers=headers, timeout=300.0)
        except httpx.RequestError as e:
            last_error = str(e)
            await _mark(ctx, att, False)
            continue
        if resp.status_code in RETRYABLE:
            last_status = resp.status_code
            last_error = resp.text[:500]
            await _mark(ctx, att, False)
            continue

        latency = int((time.time() - started) * 1000)
        data, usage_obj = None, {}
        raw_json = None
        if resp.headers.get("content-type", "").startswith("application/json"):
            try:
                raw_json = resp.json()
            except Exception:
                raw_json = None
        err = None
        if resp.status_code >= 400:
            err = (json.dumps(raw_json) if raw_json is not None else resp.text)[:500]
            await _mark(ctx, att, False)
        elif raw_json is not None:
            # 经适配器转回 OpenAI 格式
            data, usage_obj = adapter.parse_response(raw_json)
            await _mark(ctx, att, True)

        await _finalize(ctx, model=model, upstream_model=att.upstream_model, channel=att.channel,
                        status=resp.status_code, latency_ms=latency, usage_obj=usage_obj,
                        stream=False, error=err)
        if data is not None:
            return JSONResponse(status_code=resp.status_code, content=data)
        if raw_json is not None:
            return JSONResponse(status_code=resp.status_code, content=raw_json)
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


def _err_body(text: str, status: int) -> dict:
    try:
        return json.loads(text)
    except Exception:
        return {"error": {"message": text[:500], "upstream_status": status}}


async def _mark(ctx: ForwardContext, att, ok: bool) -> None:
    """上报渠道健康状态（若巡检服务可用）。"""
    if ctx.health is not None and getattr(att, "channel_id", None):
        try:
            await ctx.health.report(att.channel_id, ok)
        except Exception:
            pass


async def _stream_iter(ctx: ForwardContext, adapter, resp, model, att, started):
    captured = None
    try:
        async for out_bytes, usage in adapter.iter_stream(resp):
            if usage and usage.get("total_tokens") is not None:
                captured = usage
            yield out_bytes
    finally:
        latency = int((time.time() - started) * 1000)
        status = resp.status_code
        try:
            await resp.aclose()
        except Exception:
            pass
        await _finalize(ctx, model=model, upstream_model=att.upstream_model, channel=att.channel,
                        status=status, latency_ms=latency, usage_obj=captured or {},
                        stream=True, error=None)
