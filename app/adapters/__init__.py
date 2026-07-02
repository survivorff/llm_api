"""协议适配器：把上游各家协议统一成 OpenAI Chat 表示。

- openai：透传（DeepSeek/Qwen/Moonshot/OpenRouter 等 OpenAI 兼容上游）
- claude：Anthropic Messages ⇄ OpenAI 互转
- gemini：Google Generative Language ⇄ OpenAI 互转

按渠道 type 选择适配器；未知 type 回退 OpenAI。
"""
from __future__ import annotations

from .base import Adapter, sse
from .claude import ClaudeAdapter
from .gemini import GeminiAdapter
from .openai import OpenAIAdapter

_REGISTRY: dict[str, Adapter] = {
    "openai": OpenAIAdapter(),
    "claude": ClaudeAdapter(),
    "anthropic": ClaudeAdapter(),
    "gemini": GeminiAdapter(),
    "google": GeminiAdapter(),
}


def get_adapter(channel_type: str | None) -> Adapter:
    return _REGISTRY.get((channel_type or "openai").lower(), _REGISTRY["openai"])


__all__ = ["Adapter", "get_adapter", "sse", "OpenAIAdapter", "ClaudeAdapter", "GeminiAdapter"]
