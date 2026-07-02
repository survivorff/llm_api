"""协议适配器基类。

职责：把「内部统一表示（OpenAI Chat 格式）」与「上游真实协议」互相转换。
- build_request：内部 payload → 上游 (url, headers, body)
- parse_response：上游非流式响应 → (openai_response_dict, usage_dict)
- iter_stream：上游流式原始字节 → 产出 OpenAI 兼容 SSE 行，并捕获 usage

这样转发层 proxy 只跟统一表示打交道，新增上游只需实现一个适配器。
"""
from __future__ import annotations

from typing import AsyncIterator


class Adapter:
    #: 该适配器对应的渠道 type
    type: str = "openai"

    #: 支持的端点（openai 路径），用于校验
    endpoints: tuple[str, ...] = ("chat", "embeddings", "images", "models")

    def build_request(
        self, base_url: str, upstream_model: str, api_key: str,
        payload: dict, extra_headers: dict, endpoint: str = "chat",
    ) -> tuple[str, dict, dict]:
        """返回 (url, headers, body)。默认 OpenAI 兼容透传。"""
        raise NotImplementedError

    def parse_response(self, data: dict) -> tuple[dict, dict]:
        """上游非流式响应 → (OpenAI 格式响应, usage)。默认透传。"""
        return data, (data.get("usage") or {})

    async def iter_stream(self, resp) -> AsyncIterator[tuple[bytes, dict | None]]:
        """产出 (要下发给客户端的字节, 捕获到的 usage 或 None)。默认 OpenAI SSE 透传。"""
        raise NotImplementedError


def sse(data: str) -> bytes:
    return f"data: {data}\n\n".encode("utf-8")
