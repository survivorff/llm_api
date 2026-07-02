"""支付适配器注册表（可插拔）。

部署者通过 settings.payment_providers（JSON）启用并配置支付渠道。
未配置则订单接口对该方式返回未启用。核心不绑定任何一家支付。
"""
from __future__ import annotations

from .base import CallbackResult, PaymentProvider, PaymentRequest, PaymentResult
from .crypto import CryptoProvider
from .epay import EPayProvider

_PROVIDER_CLASSES: dict[str, type[PaymentProvider]] = {
    "epay": EPayProvider,
    "wechat": EPayProvider,   # 易支付聚合下的微信通道
    "alipay": EPayProvider,   # 易支付聚合下的支付宝通道
    "crypto": CryptoProvider,
}


def build_providers(config: dict) -> dict[str, PaymentProvider]:
    """根据配置实例化启用的 provider。

    config 形如：
      {"epay": {"api_url": ..., "pid": ..., "key": ...},
       "crypto": {"address": ...}}
    """
    out: dict[str, PaymentProvider] = {}
    for name, cfg in (config or {}).items():
        cls = _PROVIDER_CLASSES.get(name)
        if cls and isinstance(cfg, dict) and cfg.get("enabled", True):
            out[name] = cls(cfg)
    return out


__all__ = [
    "PaymentProvider", "PaymentRequest", "PaymentResult", "CallbackResult",
    "EPayProvider", "CryptoProvider", "build_providers",
]
