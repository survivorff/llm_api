"""Google Gemini（Generative Language API）适配器。

上游是 Gemini 原生 `:generateContent` / `:streamGenerateContent`。适配器负责：
- 入站 OpenAI Chat 请求 → Gemini generateContent 请求
- Gemini 响应 → OpenAI Chat 响应
- Gemini SSE 流 → OpenAI Chat SSE 流（并捕获 usage）
"""
from __future__ import annotations

import json
import time
import uuid
from typing import AsyncIterator

from .base import Adapter, sse


def _to_gemini_parts(content) -> list[dict]:
    if isinstance(content, str):
        return [{"text": content}]
    parts = []
    if isinstance(content, list):
        for p in content:
            if not isinstance(p, dict):
                continue
            if p.get("type") == "text":
                parts.append({"text": p.get("text", "")})
            elif p.get("type") == "image_url":
                url = (p.get("image_url") or {}).get("url", "")
                if url.startswith("data:"):
                    try:
                        meta, b64 = url.split(",", 1)
                        mime = meta.split(":", 1)[1].split(";", 1)[0]
                        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
                    except Exception:
                        pass
    return parts or [{"text": ""}]


class GeminiAdapter(Adapter):
    type = "gemini"
    endpoints = ("chat",)

    def build_request(self, base_url, upstream_model, api_key, payload, extra_headers, endpoint="chat"):
        messages = payload.get("messages") or []
        system_instruction = None
        contents = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                sys_parts = _to_gemini_parts(m.get("content"))
                system_instruction = {"parts": sys_parts}
                continue
            g_role = "model" if role == "assistant" else "user"
            contents.append({"role": g_role, "parts": _to_gemini_parts(m.get("content"))})

        gen_config = {}
        if payload.get("temperature") is not None:
            gen_config["temperature"] = payload["temperature"]
        if payload.get("top_p") is not None:
            gen_config["topP"] = payload["top_p"]
        if payload.get("max_tokens") is not None:
            gen_config["maxOutputTokens"] = payload["max_tokens"]

        body: dict = {"contents": contents}
        if system_instruction:
            body["systemInstruction"] = system_instruction
        if gen_config:
            body["generationConfig"] = gen_config

        model = upstream_model or payload.get("model")
        stream = bool(payload.get("stream"))
        verb = "streamGenerateContent" if stream else "generateContent"
        # key 通过 query 参数传递（Gemini 习惯）
        sep = "&" if "?" in base_url else "?"
        alt = "&alt=sse" if stream else ""
        url = f"{base_url}/models/{model}:{verb}{sep}key={api_key}{alt}"
        headers = {"Content-Type": "application/json"}
        headers.update({k: v for k, v in (extra_headers or {}).items()})
        return url, headers, body

    def _usage_from(self, meta: dict) -> dict:
        prompt = meta.get("promptTokenCount")
        completion = meta.get("candidatesTokenCount")
        total = meta.get("totalTokenCount")
        cached = meta.get("cachedContentTokenCount")
        usage = {"prompt_tokens": prompt, "completion_tokens": completion,
                 "total_tokens": total or ((prompt or 0) + (completion or 0) or None)}
        if cached is not None:
            usage["prompt_tokens_details"] = {"cached_tokens": cached}
        return usage

    def _text_from(self, candidate: dict) -> str:
        parts = ((candidate or {}).get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))

    def parse_response(self, data):
        candidates = data.get("candidates") or [{}]
        text = self._text_from(candidates[0])
        usage = self._usage_from(data.get("usageMetadata") or {})
        finish_map = {"MAX_TOKENS": "length", "STOP": "stop"}
        finish = finish_map.get((candidates[0] or {}).get("finishReason"), "stop")
        openai_resp = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": data.get("modelVersion"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": finish}],
            "usage": usage,
        }
        return openai_resp, usage

    async def iter_stream(self, resp) -> AsyncIterator[tuple[bytes, dict | None]]:
        cmpl_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())
        pending = ""

        def chunk(delta: dict, finish=None, model=None):
            obj = {"id": cmpl_id, "object": "chat.completion.chunk", "created": created,
                   "model": model, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
            return sse(json.dumps(obj, ensure_ascii=False))

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
                candidates = evt.get("candidates") or []
                model = evt.get("modelVersion")
                if candidates:
                    text = self._text_from(candidates[0])
                    if text:
                        yield chunk({"content": text}, model=model), None
                meta = evt.get("usageMetadata")
                if meta:
                    captured = self._usage_from(meta)
                    finish = (candidates[0] or {}).get("finishReason") if candidates else None
                    if finish:
                        fr = "length" if finish == "MAX_TOKENS" else "stop"
                        yield chunk({}, finish=fr, model=model), captured
        yield sse("[DONE]"), None
        await resp.aclose()
