"""路由：把请求的 model 映射到渠道，生成带 key 轮询 + 故障转移的尝试列表。"""
import threading


class NoChannelError(Exception):
    pass


class Attempt:
    """一次上游尝试：去哪个渠道、用哪个 key、上游模型名是什么。"""

    def __init__(self, channel, base_url, upstream_model, api_key, headers):
        self.channel = channel
        self.base_url = base_url
        self.upstream_model = upstream_model
        self.api_key = api_key
        self.headers = headers or {}

    @property
    def url(self) -> str:
        return f"{self.base_url}/chat/completions"


def _is_prefix(pattern: str, model: str) -> bool:
    return pattern.endswith("*") and pattern != "*" and model.startswith(pattern[:-1])


class Router:
    def __init__(self, config: dict):
        self.channels = config["channels"]
        self._rr = {}            # 渠道名 -> 轮询计数
        self._lock = threading.Lock()

    def _next_index(self, ch) -> int:
        n = len(ch["api_keys"])
        with self._lock:
            i = self._rr.get(ch["name"], 0)
            self._rr[ch["name"]] = (i + 1) % n
        return i % n

    def _upstream_model(self, ch, model: str) -> str:
        return ch.get("model_map", {}).get(model, model)

    def resolve(self, model: str):
        """返回有序的 Attempt 列表：精确匹配 → 前缀匹配 → 通配兜底，每个渠道展开所有 key。"""
        exact, prefix, wildcard = [], [], []
        for c in self.channels:
            models = c["models"]
            if model in models:
                exact.append(c)
            elif any(_is_prefix(m, model) for m in models):
                prefix.append(c)
            elif "*" in models:
                wildcard.append(c)

        seen, chosen = set(), []
        for c in exact + prefix + wildcard:
            if c["name"] not in seen:
                seen.add(c["name"])
                chosen.append(c)
        if not chosen:
            raise NoChannelError(f"no channel configured for model '{model}'")

        attempts = []
        for c in chosen:
            start = self._next_index(c)
            n = len(c["api_keys"])
            for j in range(n):
                key = c["api_keys"][(start + j) % n]
                attempts.append(
                    Attempt(c["name"], c["base_url"], self._upstream_model(c, model), key, c["headers"])
                )
        return attempts

    def list_models(self):
        """对外暴露的模型清单（跳过通配/前缀，包含 model_map 别名）。"""
        out, seen = [], set()
        for c in self.channels:
            names = [m for m in c["models"] if m != "*" and not m.endswith("*")]
            names += list(c.get("model_map", {}).keys())
            for m in names:
                if m not in seen:
                    seen.add(m)
                    out.append((m, c["name"]))
        return out
