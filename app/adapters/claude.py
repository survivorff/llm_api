"""Anthropic Claude Messages 适配器。

上游是 Anthropic 原生 `/v1/messages` 协议。适配器负责：
- 入站 OpenAI Chat 请求 → Anthropic Messages 请求
- Anthropic 非流式响应 → OpenAI Chat 响应
- Anthropic SSE 事件流 → OpenAI Chat SSE 流（并捕获 usage）

用于直连 Anthropic 官方 / 兼容 Anthropic 协议的中转上游。
"""
from __future__ import annotations

import json
import time
import uuid
from typing import AsyncIterator

from .base import Adapter, sse

DEFAULT_ANTHROPIC_VERSION = "2023-06-01"


def _split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """抽出 system 消息（Anthropic 用顶层 system 字段），其余转为 messages。"""
    system_parts: list[str] = []
    conv: list[dict] = []
    for m in messages or []:
        role = m.get("role")
        content = m.get("content")
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                system_parts += [p.get("text", "") for p in content if isinstance(p, dict)]
            continue
        conv.append(m)
    system = "\n\n".join([s for s in system_parts if s]) or None
    return system, conv


def _to_anthropic_content(content) -> list[dict] | str:
    """OpenAI message.content → Anthropic content blocks。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        blocks = []
        for part in content:
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")
            if ptype == "text":
                blocks.append({"type": "text", "text": part.get("text", "")})
            elif ptype == "image_url":
                url = (part.get("image_url") or {}).get("url", "")
                if url.startswith("data:"):
                    # data:image/png;base64,xxxx
                    try:
                        meta, b64 = url.split(",", 1)
                        media_type = meta.split(":", 1)[1].split(";", 1)[0]
                        blocks.append({
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": b64},
                        })
                    except Exception:
                        pass
                else:
                    blocks.append({"type": "image", "source": {"type": "url", "url": url}})
        return blocks or ""
    return ""


class ClaudeAdapter(Adapter):
    type = "anthropic"
    endpoints = ("chat", "messages")

    def build_request(self, base_url, upstream_model, api_key, payload, extra_headers, endpoint="chat"):
        # 若客户端已用 Anthropic 原生格式（有 system/顶层），直接透传
        messages = payload.get("messages") or []
        system, conv = _split_system(messages)

        anth_messages = []
        for m in conv:
            role = "assistant" if m.get("role") == "assistant" else "user"
            anth_messages.append({"role": role, "content": _to_anthropic_content(m.get("content"))})

        body: dict = {
            "model": upstream_model or payload.get("model"),
            "messages": anth_messages,
            "max_tokens": payload.get("max_tokens") or 4096,
        }
        if system:
            body["system"] = system
        for k_src, k_dst in (("temperature", "temperature"), ("top_p", "top_p"),
                             ("stop", "stop_sequences")):
            if payload.get(k_src) is not None:
                body[k_dst] = payload[k_src]
        if payload.get("stream"):
            body["stream"] = True

        url = f"{base_url}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": (extra_headers or {}).get("anthropic-version", DEFAULT_ANTHROPIC_VERSION),
            "Content-Type": "application/json",
        }
        # 允许额外 header 覆盖（但不覆盖 x-api-key）
        for k, v in (extra_headers or {}).items():
            if k.lower() != "x-api-key":
                headers[k] = v
        return url, headers, body

    def parse_response(self, data):
        """Anthropic messages 响应 → OpenAI chat 响应。"""
        text_parts = []
        for block in data.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        usage_in = data.get("usage") or {}
        prompt = usage_in.get("input_tokens")
        completion = usage_in.get("output_tokens")
        cached = usage_in.get("cache_read_input_tokens")
        usage = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": (prompt or 0) + (completion or 0) if (prompt or completion) else None,
        }
        if cached is not None:
            usage["prompt_tokens_details"] = {"cached_tokens": cached}
        finish = "stop"
        if data.get("stop_reason") == "max_tokens":
            finish = "length"
        openai_resp = {
            "id": data.get("id") or f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": data.get("model"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "".join(text_parts)},
                "finish_reason": finish,
            }],
            "usage": usage,
        }
        return openai_resp, usage

    async def iter_stream(self, resp) -> AsyncIterator[tuple[bytes, dict | None]]:
        """Anthropic SSE → OpenAI chat.completion.chunk SSE。"""
        cmpl_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())
        model = None
        prompt_tokens = 0
        pending = ""

        def chunk(delta: dict, finish=None):
            obj = {
                "id": cmpl_id, "object": "chat.completion.chunk", "created": created,
                "model": model, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }
            return sse(json.dumps(obj, ensure_ascii=False))

        # 首个 role chunk
        yield chunk({"role": "assistant", "content": ""}), None

        async for raw in resp.aiter_raw():
            captured = None
            pending += raw.decode("utf-8", "ignore")
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                s = line.strip()
                if not s.startswith("data:"):
                    continue
                data = s[5:].strip()
                if not data:
                    continue
                try:
                    evt = json.loads(data)
                except Exception:
                    continue
                etype = evt.get("type")
                if etype == "message_start":
                    msg = evt.get("message") or {}
                    model = msg.get("model", model)
                    u = msg.get("usage") or {}
                    prompt_tokens = u.get("input_tokens", 0) or 0
                elif etype == "content_block_delta":
                    delta = evt.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        yield chunk({"content": delta.get("text", "")}), None
                elif etype == "message_delta":
                    u = evt.get("usage") or {}
                    completion = u.get("output_tokens")
                    if completion is not None:
                        captured = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion,
                            "total_tokens": prompt_tokens + completion,
                        }
                    stop = (evt.get("delta") or {}).get("stop_reason")
                    finish = "length" if stop == "max_tokens" else "stop"
                    yield chunk({}, finish=finish), captured
                elif etype == "message_stop":
                    yield sse("[DONE]"), None

        await resp.aclose()
