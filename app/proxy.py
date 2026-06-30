"""转发：把 OpenAI 格式请求转发到上游，支持流式 + 非流式 + 故障转移 + 用量记录 + 按令牌计量。"""
import json
import time

import httpx
from fastapi.responses import JSONResponse, StreamingResponse

# 这些状态码视为可重试（换 key / 换渠道）
RETRYABLE = {429, 500, 502, 503, 504, 529}


async def forward(app, attempts, payload, stream, principal):
    client: httpx.AsyncClient = app.state.http
    db = app.state.store
    model = payload.get("model")
    token_id = principal.get("token_id")
    token_name = principal.get("name")
    last_error, last_status = None, None

    for att in attempts:
        body = dict(payload)
        body["model"] = att.upstream_model
        headers = {"Authorization": f"Bearer {att.api_key}", "Content-Type": "application/json"}
        headers.update(att.headers)
        started = time.time()

        if stream:
            if "stream_options" not in body:
                # 让上游在末尾返回 usage，便于按 token 计量
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
                _stream_iter(resp, db, model, att, principal, started),
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
        data, usage = None, {}
        if resp.headers.get("content-type", "").startswith("application/json"):
            try:
                data = resp.json()
                usage = data.get("usage") or {}
            except Exception:
                data = None
        err = None
        if resp.status_code >= 400:
            err = (json.dumps(data) if data is not None else resp.text)[:500]

        total = usage.get("total_tokens")
        db.log(model=model, upstream_model=att.upstream_model, channel=att.channel,
               status=resp.status_code, latency_ms=latency,
               prompt_tokens=usage.get("prompt_tokens"),
               completion_tokens=usage.get("completion_tokens"), total_tokens=total,
               stream=False, token_id=token_id, token_name=token_name, error=err)
        if resp.status_code < 400:
            db.add_usage(token_id, total)
        if data is not None:
            return JSONResponse(status_code=resp.status_code, content=data)
        return JSONResponse(status_code=resp.status_code, content={"raw": resp.text})

    # 所有尝试都失败
    db.log(model=model, upstream_model=model, channel="none",
           status=last_status or 502, latency_ms=0, stream=stream,
           token_id=token_id, token_name=token_name, error=last_error or "all upstreams failed")
    return JSONResponse(
        status_code=502,
        content={"error": {"message": last_error or "all upstreams failed", "upstream_status": last_status}},
    )


async def _stream_iter(resp, db, model, att, principal, started):
    pending = ""
    captured = None
    try:
        async for chunk in resp.aiter_raw():
            yield chunk
            # 边转发边解析 SSE，捕获末尾的 usage 用于按 token 计量
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
        total = captured.get("total_tokens") if captured else None
        db.log(model=model, upstream_model=att.upstream_model, channel=att.channel,
               status=status, latency_ms=latency,
               prompt_tokens=captured.get("prompt_tokens") if captured else None,
               completion_tokens=captured.get("completion_tokens") if captured else None,
               total_tokens=total, stream=True,
               token_id=principal.get("token_id"), token_name=principal.get("name"), error=None)
        if total:
            db.add_usage(principal.get("token_id"), total)
