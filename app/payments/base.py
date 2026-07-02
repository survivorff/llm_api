"""支付适配器接口（可插拔）。

设计目标：部署者按需启用支付渠道，核心不绑定任何一家。
每个 provider 实现三件事：
- create_payment：创建支付（返回跳转/二维码/收款地址）
- verify_callback：校验异步回调（验签），返回 (order_no, provider_order, ok)
- query_status：主动查询订单状态（对账 worker 用），返回是否已支付

金额单位：credits（内部）与 amount_money（最小货币单位）由订单服务换算，
provider 只关心 amount_money + currency。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaymentRequest:
    order_no: str
    amount_money: int          # 最小货币单位（分 / satoshi 等）
    currency: str = "CNY"
    subject: str = "credits topup"
    extra: dict = field(default_factory=dict)


@dataclass
class PaymentResult:
    """创建支付的返回。"""
    ok: bool
    pay_url: str | None = None       # 跳转 URL 或二维码内容
    pay_address: str | None = None   # 加密货币收款地址
    provider_order: str | None = None
    extra: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class CallbackResult:
    ok: bool                    # 验签是否通过且支付成功
    order_no: str | None = None
    provider_order: str | None = None
    amount_money: int | None = None
    raw: dict = field(default_factory=dict)


class PaymentProvider:
    """支付 provider 基类。"""

    #: provider 标识（wechat/alipay/crypto/...）
    name: str = "base"
    #: 是否需要异步回调（False 则完全靠对账 worker 轮询）
    supports_callback: bool = True

    def __init__(self, config: dict):
        self.config = config or {}

    async def create_payment(self, req: PaymentRequest) -> PaymentResult:
        raise NotImplementedError

    def verify_callback(self, headers: dict, body: bytes, form: dict) -> CallbackResult:
        """校验回调并解析。默认不支持。"""
        return CallbackResult(ok=False)

    async def query_status(self, order_no: str, provider_order: str | None) -> bool:
        """主动查询是否已支付。默认未支付。"""
        return False
