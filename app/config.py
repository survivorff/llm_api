"""配置加载：读取 YAML + 用环境变量替换 ${VAR}，并归一化。"""
import os
import re

import yaml

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _interpolate(value):
    """递归把字符串里的 ${ENV} 替换成环境变量值（缺省为空串）。"""
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    return value


def normalize_config(raw: dict) -> dict:
    """归一化：过滤无有效 key 的渠道、补默认值。"""
    cfg = {
        "server": raw.get("server") or {},
        "auth": raw.get("auth") or {},
        "logging": raw.get("logging") or {},
        "channels": [],
    }
    for ch in raw.get("channels") or []:
        keys = [str(k).strip() for k in (ch.get("api_keys") or []) if k and str(k).strip()]
        if not keys:
            # 没有有效 key → 该渠道未启用，跳过
            continue
        cfg["channels"].append({
            "name": ch.get("name") or "unnamed",
            "base_url": (ch.get("base_url") or "").rstrip("/"),
            "api_keys": keys,
            "models": ch.get("models") or [],
            "model_map": ch.get("model_map") or {},
            "headers": ch.get("headers") or {},
        })

    cfg["auth"]["client_keys"] = [
        str(k).strip() for k in (cfg["auth"].get("client_keys") or []) if k and str(k).strip()
    ]
    cfg["auth"]["admin_key"] = (str(cfg["auth"].get("admin_key") or "").strip()) or None
    cfg["logging"].setdefault("db_path", "usage.db")
    cfg["server"].setdefault("host", "0.0.0.0")
    cfg["server"].setdefault("port", 8080)
    return cfg


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return normalize_config(_interpolate(raw))
