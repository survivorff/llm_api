"""轻量 Prometheus 指标（无外部依赖）。

进程内计数器/直方图，导出为 Prometheus 文本格式。多实例下各自导出，
由 Prometheus 按 instance label 聚合。够用且零依赖；需要更全可换 prometheus_client。
"""
from __future__ import annotations

import threading
import time

_lock = threading.Lock()

# 计数器：{(name, labels_tuple): value}
_counters: dict[tuple, float] = {}
# 直方图桶：{name: {"buckets": {le: count}, "sum": x, "count": n, "labels": {...}}}
_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
_hist: dict[tuple, dict] = {}

# 计量说明（HELP/TYPE）
_META = {
    "llm_api_requests_total": ("counter", "Total API requests"),
    "llm_api_request_errors_total": ("counter", "Total failed requests"),
    "llm_api_tokens_total": ("counter", "Total tokens processed"),
    "llm_api_request_duration_seconds": ("histogram", "Request duration seconds"),
}


def _key(name: str, labels: dict | None) -> tuple:
    items = tuple(sorted((labels or {}).items()))
    return (name, items)


def inc_counter(name: str, value: float = 1.0, **labels) -> None:
    k = _key(name, labels)
    with _lock:
        _counters[k] = _counters.get(k, 0.0) + value


def observe_latency(name: str, seconds: float, **labels) -> None:
    k = _key(name, labels)
    with _lock:
        h = _hist.get(k)
        if h is None:
            h = {"buckets": {le: 0 for le in _LATENCY_BUCKETS}, "sum": 0.0, "count": 0,
                 "labels": dict(labels)}
            _hist[k] = h
        h["sum"] += seconds
        h["count"] += 1
        for le in _LATENCY_BUCKETS:
            if seconds <= le:
                h["buckets"][le] += 1


def _fmt_labels(items: tuple, extra: dict | None = None) -> str:
    d = dict(items)
    if extra:
        d.update(extra)
    if not d:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in d.items())
    return "{" + inner + "}"


def render() -> str:
    """导出 Prometheus 文本格式。"""
    lines: list[str] = []
    emitted_meta: set[str] = set()

    def meta(name: str):
        if name in emitted_meta:
            return
        emitted_meta.add(name)
        typ, help_ = _META.get(name, ("untyped", name))
        lines.append(f"# HELP {name} {help_}")
        lines.append(f"# TYPE {name} {typ}")

    with _lock:
        for (name, items), val in sorted(_counters.items()):
            meta(name)
            lines.append(f"{name}{_fmt_labels(items)} {val:g}")

        for (name, items), h in sorted(_hist.items()):
            meta(name)
            cumulative = 0
            for le in _LATENCY_BUCKETS:
                cumulative = h["buckets"][le]
                lines.append(f'{name}_bucket{_fmt_labels(items, {"le": le})} {cumulative:g}')
            lines.append(f'{name}_bucket{_fmt_labels(items, {"le": "+Inf"})} {h["count"]:g}')
            lines.append(f'{name}_sum{_fmt_labels(items)} {h["sum"]:g}')
            lines.append(f'{name}_count{_fmt_labels(items)} {h["count"]:g}')

    return "\n".join(lines) + "\n"


def reset() -> None:
    """测试用：清空所有指标。"""
    with _lock:
        _counters.clear()
        _hist.clear()
