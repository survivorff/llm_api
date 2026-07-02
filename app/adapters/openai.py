"""OpenAI 兼容适配器：透传。多数国产模型（DeepSeek/Qwen/Moonshot）+ OpenRouter 均可用。"""
from __future__ import annotations

import json
from typing import AsyncIterator

from .base import Adapter

_ENDPOINT_PATHS = {
    "chat": "chat/completions",
    "embeddings": "embeddings",
    "images": "images/generations",
    "audio_speech": "audio/speech",
    "audio_transcriptions": "audio/transcriptions",
    "rerank": "rerank",
}


class OpenAIAdapter(Adapter):
    type = "openai"
    endpoints = ("chat", "embeddings", "images", "audio_speech", "rerank", "models")

    def build_request(self, base_url, upstream_model, api_key, payload, extra_headers, endpoint="chat"):
        body = dict(payload)
        if upstream_model:
            body["model"] = upstream_model
        if endpoint == "chat" and body.get("stream") and "stream_options" not in body:
            body["stream_options"] = {"include_usage": True}
        path = _ENDPOINT_PATHS.get(endpoint, "chat/completions")
        url = f"{base_url}/{path}"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        headers.update(extra_headers or {})
        return url, headers, body

    def parse_response(self, data):
        return data, (data.get("usage") or {})

    async def iter_stream(self, resp) -> AsyncIterator[tuple[bytes, dict | None]]:
        pending = ""
        async for chunk in resp.aiter_raw():
            captured = None
            pending += chunk.decode("utf-8", "ignore")
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                s = line.strip()
                if s.startswith("data:"):
                    data = s[5:].strip()
                    if data and data != "[DONE]":
                        try:
                            obj = json.loads(data)
                            u = obj.get("usage")
                            if u and u.get("total_tokens") is not None:
                                captured = u
                        except Exception:
                            pass
            yield chunk, captured
